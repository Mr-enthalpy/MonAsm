/*
 * n1b_poc.c - platform feasibility probe for the N1b open-time guarantee.
 *
 * Evidence only. This file is not a product dependency and is never read by
 * the build. It answers one question per platform: can a reader open a child
 * entry relative to an already-open directory handle, refuse links/reparse
 * points at every component, and refuse a non-regular leaf before any
 * potentially blocking read?
 *
 * Platform mechanisms:
 *   Linux   openat2(RESOLVE_NO_SYMLINKS | RESOLVE_NO_MAGICLINKS), per component
 *   macOS   openat(O_NOFOLLOW) per component, since the dirfd fixes the parent
 *   Windows NtCreateFile(RootDirectory=handle, FILE_OPEN_REPARSE_POINT), then
 *           FileAttributeTagInfo reports FILE_ATTRIBUTE_REPARSE_POINT
 *
 * Cases:
 *   plain                  ordinary nested file opens and reads
 *   intermediate_link      a link/junction used as an intermediate directory
 *   final_link             a link used as the final file entry
 *   final_reparse_dir      a junction opened as a file (Windows only)
 *   fifo                   POSIX FIFO leaf rejected as not-a-regular-file
 *                          without blocking (POSIX only)
 *   swap                   parent path replaced after the handle is open; the
 *                          child still comes from the original directory
 *
 * Exit code 0 only when every required case passes. A case whose fixture
 * cannot be created is reported SKIP, never PASS.
 */

#if !defined(_WIN32)
#define _POSIX_C_SOURCE 200809L
#define _DEFAULT_SOURCE 1
#if defined(__APPLE__)
#define _DARWIN_C_SOURCE 1
#endif
#if defined(__linux__)
#define _GNU_SOURCE 1
#endif
#endif

#if defined(_WIN32)
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <winternl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#else
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/utsname.h>
#include <time.h>
#include <unistd.h>
#if defined(__linux__)
#include <sys/syscall.h>
#ifndef SYS_openat2
#define SYS_openat2 437
#endif
#ifndef RESOLVE_NO_MAGICLINKS
#define RESOLVE_NO_MAGICLINKS 0x02
#endif
#ifndef RESOLVE_NO_SYMLINKS
#define RESOLVE_NO_SYMLINKS 0x04
#endif
struct n1b_open_how {
  unsigned long long flags;
  unsigned long long mode;
  unsigned long long resolve;
};
#endif
#endif

#define CONTENT "hello-n1b"
#define ORIGINAL "original-dir"
#define HIJACKED "hijacked-dir"

static int failures;

#if defined(_WIN32)

typedef NTSTATUS (NTAPI *PFN_NtCreateFile)(PHANDLE, ACCESS_MASK, POBJECT_ATTRIBUTES,
                                           PIO_STATUS_BLOCK, PLARGE_INTEGER, ULONG,
                                           ULONG, ULONG, ULONG, PVOID, ULONG);
typedef LONG (WINAPI *PFN_RtlGetVersion)(PRTL_OSVERSIONINFOW);

static PFN_NtCreateFile p_NtCreateFile;
static PFN_RtlGetVersion p_RtlGetVersion;

typedef struct { HANDLE h; } dir_handle;
typedef struct { HANDLE h; } file_handle;

static dir_handle dh_new(void) { dir_handle d; d.h = INVALID_HANDLE_VALUE; return d; }
static file_handle fh_new(void) { file_handle f; f.h = INVALID_HANDLE_VALUE; return f; }

static void platform_name(char *out, size_t cap) {
  RTL_OSVERSIONINFOW vi;
  memset(&vi, 0, sizeof(vi));
  vi.dwOSVersionInfoSize = sizeof(vi);
  if (p_RtlGetVersion && p_RtlGetVersion(&vi) == 0)
    snprintf(out, cap, "Windows %lu.%lu build %lu", (unsigned long)vi.dwMajorVersion,
             (unsigned long)vi.dwMinorVersion, (unsigned long)vi.dwBuildNumber);
  else
    snprintf(out, cap, "Windows (version unknown)");
}

static int platform_init(void) {
  HMODULE nt = GetModuleHandleW(L"ntdll.dll");
  if (!nt) return -1;
  p_NtCreateFile = (PFN_NtCreateFile)(void *)GetProcAddress(nt, "NtCreateFile");
  p_RtlGetVersion = (PFN_RtlGetVersion)(void *)GetProcAddress(nt, "RtlGetVersion");
  return p_NtCreateFile ? 0 : -1;
}

static wchar_t *wide(const char *s) {
  int n = MultiByteToWideChar(CP_ACP, 0, s, -1, NULL, 0);
  wchar_t *w = (wchar_t *)malloc((size_t)n * sizeof(wchar_t));
  if (!w) return NULL;
  MultiByteToWideChar(CP_ACP, 0, s, -1, w, n);
  return w;
}

static int mkdir_one(const char *path) {
  wchar_t *w = wide(path);
  BOOL ok = w ? CreateDirectoryW(w, NULL) : FALSE;
  DWORD err = GetLastError();
  free(w);
  if (!ok && err != ERROR_ALREADY_EXISTS) return -1;
  return 0;
}

static int write_file(const char *path, const char *data) {
  wchar_t *w = wide(path);
  HANDLE h = w ? CreateFileW(w, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS,
                             FILE_ATTRIBUTE_NORMAL, NULL)
               : INVALID_HANDLE_VALUE;
  free(w);
  if (h == INVALID_HANDLE_VALUE) return -1;
  DWORD written = 0;
  BOOL ok = WriteFile(h, data, (DWORD)strlen(data), &written, NULL);
  CloseHandle(h);
  return ok && written == (DWORD)strlen(data) ? 0 : -1;
}

static int make_symlink(const char *link, const char *target, int is_dir) {
  wchar_t *wl = wide(link);
  wchar_t *wt = wide(target);
  DWORD flags = is_dir ? SYMBOLIC_LINK_FLAG_DIRECTORY : 0;
  BOOL ok = wl && wt ? CreateSymbolicLinkW(wl, wt, flags) : FALSE;
  free(wl);
  free(wt);
  return ok ? 0 : -(int)GetLastError();
}

static int make_junction(const char *link, const char *target) {
  char cmd[2048];
  snprintf(cmd, sizeof(cmd), "cmd /c mklink /J \"%s\" \"%s\" >NUL 2>&1", link, target);
  return system(cmd) == 0 ? 0 : -1;
}

static int dir_open_root(const char *path, dir_handle *out) {
  wchar_t *w = wide(path);
  HANDLE h = w ? CreateFileW(w, FILE_LIST_DIRECTORY | FILE_READ_ATTRIBUTES | SYNCHRONIZE,
                             FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                             NULL, OPEN_EXISTING,
                             FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, NULL)
              : INVALID_HANDLE_VALUE;
  free(w);
  if (h == INVALID_HANDLE_VALUE) return -3;
  out->h = h;
  return 0;
}

static int classify(HANDLE h, int want_dir, char *detail, size_t cap) {
  FILE_ATTRIBUTE_TAG_INFO ti;
  if (!GetFileInformationByHandleEx(h, FileAttributeTagInfo, &ti, sizeof(ti))) {
    snprintf(detail, cap, "FileAttributeTagInfo error %lu", (unsigned long)GetLastError());
    return -3;
  }
  if (ti.FileAttributes & FILE_ATTRIBUTE_REPARSE_POINT) {
    snprintf(detail, cap, "reparse tag 0x%08lx", (unsigned long)ti.ReparseTag);
    return -1;
  }
  if (want_dir) {
    if (!(ti.FileAttributes & FILE_ATTRIBUTE_DIRECTORY)) {
      snprintf(detail, cap, "not a directory");
      return -3;
    }
  } else {
    if (ti.FileAttributes & FILE_ATTRIBUTE_DIRECTORY) {
      snprintf(detail, cap, "is a directory");
      return -2;
    }
    if (GetFileType(h) != FILE_TYPE_DISK) {
      snprintf(detail, cap, "file type %lu", (unsigned long)GetFileType(h));
      return -2;
    }
  }
  return 0;
}

static int nt_open(HANDLE root, const char *name, int is_dir, HANDLE *out,
                   char *detail, size_t cap) {
  wchar_t *wn = wide(name);
  if (!wn) return -3;
  UNICODE_STRING us;
  us.Buffer = (PWSTR)wn;
  us.Length = (USHORT)(wcslen(wn) * sizeof(WCHAR));
  us.MaximumLength = us.Length + sizeof(WCHAR);
  OBJECT_ATTRIBUTES oa;
  InitializeObjectAttributes(&oa, &us, OBJ_CASE_INSENSITIVE, root, NULL);
  IO_STATUS_BLOCK iosb;
  ACCESS_MASK access = is_dir
      ? (FILE_LIST_DIRECTORY | FILE_READ_ATTRIBUTES | SYNCHRONIZE)
      : (FILE_READ_DATA | FILE_READ_ATTRIBUTES | SYNCHRONIZE);
  ULONG options = FILE_OPEN_REPARSE_POINT | FILE_SYNCHRONOUS_IO_NONALERT |
                  (is_dir ? FILE_DIRECTORY_FILE : FILE_NON_DIRECTORY_FILE);
  HANDLE h = NULL;
  NTSTATUS st = p_NtCreateFile(&h, access, &oa, &iosb, NULL, FILE_ATTRIBUTE_NORMAL,
                               FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                               FILE_OPEN, options, NULL, 0);
  free(wn);
  if (st < 0) {
    snprintf(detail, cap, "NtCreateFile status 0x%08lx", (unsigned long)st);
    return -3;
  }
  int rc = classify(h, is_dir, detail, cap);
  if (rc != 0) {
    CloseHandle(h);
    return rc;
  }
  *out = h;
  return 0;
}

static int dir_open_sub(dir_handle *parent, const char *name, dir_handle *out,
                        char *detail, size_t cap) {
  HANDLE h = NULL;
  int rc = nt_open(parent->h, name, 1, &h, detail, cap);
  if (rc == 0) out->h = h;
  return rc;
}

static int file_open(dir_handle *parent, const char *name, file_handle *out,
                     char *detail, size_t cap) {
  HANDLE h = NULL;
  int rc = nt_open(parent->h, name, 0, &h, detail, cap);
  if (rc == 0) out->h = h;
  return rc;
}

static int file_read_all(file_handle *f, char *buf, size_t cap) {
  DWORD got = 0;
  if (!ReadFile(f->h, buf, (DWORD)(cap - 1), &got, NULL)) return -1;
  buf[got] = 0;
  return (int)got;
}

static void file_close(file_handle *f) {
  if (f->h && f->h != INVALID_HANDLE_VALUE) CloseHandle(f->h);
  f->h = INVALID_HANDLE_VALUE;
}

static void dir_close(dir_handle *d) {
  if (d->h && d->h != INVALID_HANDLE_VALUE) CloseHandle(d->h);
  d->h = INVALID_HANDLE_VALUE;
}

static void platform_api(char *out, size_t cap) {
  snprintf(out, cap, "NtCreateFile(RootDirectory=dir handle, FILE_OPEN_REPARSE_POINT)");
}

#else /* POSIX */

typedef struct { int fd; } dir_handle;
typedef struct { int fd; } file_handle;

static dir_handle dh_new(void) { dir_handle d; d.fd = -1; return d; }
static file_handle fh_new(void) { file_handle f; f.fd = -1; return f; }

static void platform_name(char *out, size_t cap) {
  struct utsname u;
  if (uname(&u) == 0) snprintf(out, cap, "%s %s", u.sysname, u.release);
  else snprintf(out, cap, "unknown");
}

static int platform_init(void) { return 0; }

static int mkdir_one(const char *path) {
  if (mkdir(path, 0700) == 0) return 0;
  return errno == EEXIST ? 0 : -1;
}

static int write_file(const char *path, const char *data) {
  int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0600);
  if (fd < 0) return -1;
  size_t len = strlen(data);
  ssize_t n = write(fd, data, len);
  close(fd);
  return n == (ssize_t)len ? 0 : -1;
}

static int make_symlink(const char *link, const char *target, int is_dir) {
  (void)is_dir;
  return symlink(target, link) == 0 ? 0 : -errno;
}

static int make_junction(const char *link, const char *target) {
  (void)link;
  (void)target;
  return -1;
}

static int dir_open_root(const char *path, dir_handle *out) {
  int fd = open(path, O_RDONLY | O_DIRECTORY | O_CLOEXEC);
  if (fd < 0) return -3;
  out->fd = fd;
  return 0;
}

static int classify(int fd, int want_dir, char *detail, size_t cap) {
  struct stat st;
  if (fstat(fd, &st) != 0) {
    snprintf(detail, cap, "fstat errno %d", errno);
    return -3;
  }
  if (S_ISLNK(st.st_mode)) {
    snprintf(detail, cap, "symbolic link");
    return -1;
  }
  if (want_dir) {
    if (!S_ISDIR(st.st_mode)) {
      snprintf(detail, cap, "not a directory");
      return -3;
    }
  } else if (!S_ISREG(st.st_mode)) {
    snprintf(detail, cap, "mode 0%o", (unsigned)st.st_mode);
    return -2;
  }
  return 0;
}

static int open_sub(int parent, const char *name, int is_dir, char *detail,
                    size_t cap) {
  int flags = O_RDONLY | O_CLOEXEC | O_NOFOLLOW;
  flags |= is_dir ? O_DIRECTORY : O_NONBLOCK;
#if defined(__linux__)
  struct n1b_open_how how;
  memset(&how, 0, sizeof(how));
  how.flags = (unsigned long long)flags;
  how.resolve = RESOLVE_NO_SYMLINKS | RESOLVE_NO_MAGICLINKS;
  int fd = (int)syscall(SYS_openat2, parent, name, &how, sizeof(how));
#else
  int fd = openat(parent, name, flags);
#endif
  if (fd < 0) {
    int e = errno;
#if defined(__linux__)
    if (e == ELOOP || e == EXDEV || e == ENOTDIR) {
#else
    if (e == ELOOP || e == EMLINK || e == ENOTDIR) {
#endif
      snprintf(detail, cap, "open refused with errno %d (%s)", e, strerror(e));
      return -1;
    }
    snprintf(detail, cap, "open failed errno %d (%s)", e, strerror(e));
    return -3;
  }
  int rc = classify(fd, is_dir, detail, cap);
  if (rc != 0) {
    close(fd);
    return rc;
  }
  return fd;
}

static int dir_open_sub(dir_handle *parent, const char *name, dir_handle *out,
                        char *detail, size_t cap) {
  int fd = open_sub(parent->fd, name, 1, detail, cap);
  if (fd < 0) return fd;
  out->fd = fd;
  return 0;
}

static int file_open(dir_handle *parent, const char *name, file_handle *out,
                     char *detail, size_t cap) {
  int fd = open_sub(parent->fd, name, 0, detail, cap);
  if (fd < 0) return fd;
  out->fd = fd;
  return 0;
}

static int file_read_all(file_handle *f, char *buf, size_t cap) {
  ssize_t n = read(f->fd, buf, cap - 1);
  if (n < 0) return -1;
  buf[n] = 0;
  return (int)n;
}

static void file_close(file_handle *f) {
  if (f->fd >= 0) close(f->fd);
  f->fd = -1;
}

static void dir_close(dir_handle *d) {
  if (d->fd >= 0) close(d->fd);
  d->fd = -1;
}

static void platform_api(char *out, size_t cap) {
#if defined(__linux__)
  snprintf(out, cap, "openat2(RESOLVE_NO_SYMLINKS|RESOLVE_NO_MAGICLINKS) per component");
#else
  snprintf(out, cap, "openat(O_NOFOLLOW) per component against the parent dirfd");
#endif
}

#endif

static void record(const char *id, int ok, int skipped, const char *detail) {
  if (skipped) {
    printf("case %-20s expected=%-28s observed=%-28s verdict=SKIP detail=%s\n",
           id, "fixture available", "not created", detail ? detail : "");
    return;
  }
  if (!ok) failures++;
  printf("case %-20s expected=%-28s observed=%-28s verdict=%s detail=%s\n",
         id, "refused or exact bytes", ok ? "as expected" : "mismatch",
         ok ? "PASS" : "FAIL", detail ? detail : "");
}

static void join(char *out, size_t cap, const char *base, const char *name) {
  snprintf(out, cap, "%s/%s", base, name);
}

static void remove_tree(const char *base) {
  char cmd[2048];
#if defined(_WIN32)
  snprintf(cmd, sizeof(cmd), "cmd /c rmdir /S /Q \"%s\" >NUL 2>&1", base);
#else
  snprintf(cmd, sizeof(cmd), "rm -rf '%s'", base);
#endif
  if (system(cmd) != 0) { /* fixture cleanup is best effort */ }
}

int main(int argc, char **argv) {
  const char *base = argc > 1 ? argv[1] : "n1b-tmp";
  char plat[256], api[256], detail[256];
  char p1[1024], p2[1024], p3[1024];
  int rc;

  if (platform_init() != 0) {
    printf("N1b-PoC fatal=platform_init_failed\n");
    return 2;
  }
  platform_name(plat, sizeof(plat));
  platform_api(api, sizeof(api));
  printf("N1b-PoC platform=\"%s\" api=\"%s\"\n", plat, api);

  remove_tree(base);
  if (mkdir_one(base) != 0) {
    printf("N1b-PoC fatal=fixture_root_failed path=%s\n", base);
    return 2;
  }
  join(p1, sizeof(p1), base, "sub");
  join(p2, sizeof(p2), base, "dir2");
  join(p3, sizeof(p3), base, "other");
  mkdir_one(p1);
  mkdir_one(p2);
  mkdir_one(p3);
  join(p1, sizeof(p1), base, "sub/f.txt");
  write_file(p1, CONTENT);
  join(p1, sizeof(p1), base, "dir2/f.txt");
  write_file(p1, ORIGINAL);
  join(p1, sizeof(p1), base, "other/f.txt");
  write_file(p1, HIJACKED);

  dir_handle root = dh_new();
  if (dir_open_root(base, &root) != 0) {
    printf("N1b-PoC fatal=root_handle_failed\n");
    return 2;
  }

  /* plain: ordinary nested read through handles. */
  {
    dir_handle sub = dh_new();
    file_handle f = fh_new();
    char buf[64] = {0};
    int ok = 0;
    detail[0] = 0;
    if (dir_open_sub(&root, "sub", &sub, detail, sizeof(detail)) == 0 &&
        file_open(&sub, "f.txt", &f, detail, sizeof(detail)) == 0 &&
        file_read_all(&f, buf, sizeof(buf)) > 0 && strcmp(buf, CONTENT) == 0)
      ok = 1;
    record("plain", ok, 0, ok ? buf : detail);
    file_close(&f);
    dir_close(&sub);
  }

  /* intermediate link: directory entry that resolves elsewhere. */
  {
    join(p1, sizeof(p1), base, "sub");
    join(p2, sizeof(p2), base, "linkdir");
#if defined(_WIN32)
    int made = make_junction(p2, p1);
    const char *kind = "junction";
#else
    int made = make_symlink(p2, p1, 1);
    const char *kind = "symlink";
#endif
    if (made != 0) {
      snprintf(detail, sizeof(detail), "%s creation failed (%d)", kind, made);
      record("intermediate_link", 0, 1, detail);
    } else {
      dir_handle l = dh_new();
      rc = dir_open_sub(&root, "linkdir", &l, detail, sizeof(detail));
      snprintf(p3, sizeof(p3), "%s refused rc=%d: %s", kind, rc, detail);
      record("intermediate_link", rc == -1, 0, p3);
      dir_close(&l);
    }
  }

  /* final link: file entry created as a link. */
  {
    join(p1, sizeof(p1), base, "sub/f.txt");
    join(p2, sizeof(p2), base, "link.txt");
#if defined(_WIN32)
    int made = make_symlink(p2, p1, 0);
    const char *kind = "file symlink";
#else
    int made = make_symlink(p2, p1, 0);
    const char *kind = "file symlink";
#endif
    if (made != 0) {
      snprintf(detail, sizeof(detail), "%s creation failed (%d)", kind, made);
      record("final_link", 0, 1, detail);
    } else {
      file_handle f = fh_new();
      rc = file_open(&root, "link.txt", &f, detail, sizeof(detail));
      snprintf(p3, sizeof(p3), "%s refused rc=%d: %s", kind, rc, detail);
      record("final_link", rc == -1, 0, p3);
      file_close(&f);
    }
  }

#if defined(_WIN32)
  /* final reparse directory opened as a file: refusal must not follow it. */
  {
    join(p1, sizeof(p1), base, "sub");
    join(p2, sizeof(p2), base, "junc_final");
    if (make_junction(p2, p1) != 0) {
      record("final_reparse_dir", 0, 1, "junction creation failed");
    } else {
      file_handle f = fh_new();
      rc = file_open(&root, "junc_final", &f, detail, sizeof(detail));
      snprintf(p3, sizeof(p3), "refused rc=%d: %s", rc, detail);
      record("final_reparse_dir", rc != 0, 0, p3);
      file_close(&f);
    }
  }
#else
  /* POSIX FIFO leaf: must be refused as non-regular without blocking. */
  {
    struct timespec t0, t1;
    join(p2, sizeof(p2), base, "fifo");
    if (mkfifo(p2, 0600) != 0) {
      record("fifo", 0, 1, "mkfifo failed");
    } else {
      file_handle f = fh_new();
      clock_gettime(CLOCK_MONOTONIC, &t0);
      rc = file_open(&root, "fifo", &f, detail, sizeof(detail));
      clock_gettime(CLOCK_MONOTONIC, &t1);
      long ms = (t1.tv_sec - t0.tv_sec) * 1000L + (t1.tv_nsec - t0.tv_nsec) / 1000000L;
      snprintf(p3, sizeof(p3), "rc=%d mode-reject=%s elapsed=%ldms", rc, detail, ms);
      record("fifo", rc == -2 && ms < 1000, 0, p3);
      file_close(&f);
    }
  }
#endif

  /* swap: replace the parent path after its handle is open. */
  {
    dir_handle d2 = dh_new();
    file_handle f = fh_new();
    char buf[64] = {0};
    int ok = 0;
    detail[0] = 0;
    if (dir_open_sub(&root, "dir2", &d2, detail, sizeof(detail)) == 0) {
      join(p1, sizeof(p1), base, "dir2");
      join(p2, sizeof(p2), base, "dir2_moved");
#if defined(_WIN32)
      {
        wchar_t *a = wide(p1);
        wchar_t *b = wide(p2);
        int moved = a && b ? MoveFileW(a, b) : 0;
        free(a);
        free(b);
        if (!moved)
          snprintf(detail, sizeof(detail), "rename failed %lu", (unsigned long)GetLastError());
      }
      join(p3, sizeof(p3), base, "other");
      if (detail[0] == 0 && make_junction(p1, p3) != 0)
        snprintf(detail, sizeof(detail), "replacement junction failed");
#else
      if (rename(p1, p2) != 0)
        snprintf(detail, sizeof(detail), "rename failed errno %d", errno);
      join(p3, sizeof(p3), base, "other");
      if (detail[0] == 0 && make_symlink(p1, p3, 1) != 0)
        snprintf(detail, sizeof(detail), "replacement symlink failed");
#endif
      if (detail[0] == 0 &&
          file_open(&d2, "f.txt", &f, detail, sizeof(detail)) == 0 &&
          file_read_all(&f, buf, sizeof(buf)) > 0 && strcmp(buf, ORIGINAL) == 0)
        ok = 1;
      snprintf(p3, sizeof(p3), "read=%s", buf);
      record("swap", ok, 0, ok ? p3 : detail);
    } else {
      record("swap", 0, 0, detail);
    }
    file_close(&f);
    dir_close(&d2);
  }

  dir_close(&root);
  printf("N1b-PoC summary platform=\"%s\" failures=%d\n", plat, failures);
  return failures == 0 ? 0 : 1;
}
