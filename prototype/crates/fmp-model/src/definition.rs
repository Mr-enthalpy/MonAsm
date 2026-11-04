//! The definition artifact of `docs/fmp-v0/07_definition_format.md`.
//!
//! A definition is data: a closed set of forms, each a hex template plus ordered
//! slots with bit placements. The loader answers two questions and refuses to
//! answer a third — there is no selection, no default and no alias here.
//!
//! Every load-time failure is `E-DEF-001` (§9), because the definition is the
//! input: a table that fails a structural check has no correct output, so it is
//! never offered to a plan. `E-DEF-002` is the registry's "not shipped" answer
//! and belongs to `Registry::find`, not to this module.

use std::path::{Path, PathBuf};

use crate::bind::{self, Obj};
use crate::codes;
use crate::diagnostic::Diagnostic;
use crate::json;
use crate::plan::Modifier;

/// A loaded, structurally valid definition document.
#[derive(Clone, Debug)]
pub struct Definition {
    pub document: json::Json,
    pub definition_format: String,
    pub namespace: String,
    pub version: String,
    pub target: DefinitionTarget,
    pub forms: Vec<Form>,
    pub digest: String,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct DefinitionTarget {
    pub isa_family: String,
    pub isa_variant: String,
    pub execution_mode: String,
    pub enabled_extensions: Vec<String>,
    pub byte_order: String,
    pub address_width: u32,
}

#[derive(Clone, Debug)]
pub struct Form {
    pub form_id: String,
    pub template: Vec<u8>,
    pub slots: Vec<Slot>,
}

#[derive(Clone, Debug)]
pub struct Slot {
    pub role: String,
    pub kind: String,
    pub target_type: String,
    pub from: SlotFrom,
    pub range: Option<Range>,
    pub modifiers: Vec<Modifier>,
    pub placements: Vec<Placement>,
    /// Exact values the slot's field may not carry, strictly increasing.
    /// Subtract from `range` (or the placements' width for `reg_number`).
    pub excluded: Vec<i128>,
    /// `sum(width)` over `placements`.
    pub width_bits: u32,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum SlotFrom {
    RegNumber,
    OperandValue,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Range {
    pub signed: bool,
    pub bits: u32,
    pub align_bits: u32,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Placement {
    /// Bit offset from the least significant bit of template byte 0.
    pub bit_offset: u32,
    pub width: u32,
}

impl Form {
    /// `size` is not a field: it is `len(template)`.
    pub fn size(&self) -> u64 {
        self.template.len() as u64
    }

    pub fn bits(&self) -> u32 {
        (self.template.len() as u32) * 8
    }
}

impl Slot {
    /// The highest bit this slot owns, exclusive.
    pub fn end_bit(&self) -> u32 {
        self.placements
            .iter()
            .map(|placement| placement.bit_offset + placement.width)
            .max()
            .unwrap_or(0)
    }

    /// The bits this slot owns, as `(offset, width)` pairs in template order.
    pub fn owned_bits(&self) -> Vec<(u32, u32)> {
        self.placements
            .iter()
            .map(|placement| (placement.bit_offset, placement.width))
            .collect()
    }
}

const DEFINITION_FIELDS: &[&str] = &[
    "definition_format",
    "namespace",
    "version",
    "target_identity",
    "forms",
];
const TARGET_FIELDS: &[&str] = &[
    "isa_family",
    "isa_variant",
    "execution_mode",
    "enabled_extensions",
    "byte_order",
    "address_width",
];
const FORM_FIELDS: &[&str] = &["form_id", "template", "slots"];
const SLOT_FIELDS: &[&str] = &[
    "role",
    "kind",
    "target_type",
    "from",
    "range",
    "excluded",
    "modifiers",
    "placements",
];
const PLACEMENT_FIELDS: &[&str] = &["bit_offset", "width"];

/// Roles the contract's operand model allows (`01_contract.md` §8).
const ROLES: &[&str] = &[
    "dest", "src", "src2", "base", "index", "disp", "imm", "target", "pred", "list", "modifier",
];

/// The encoding families `07_definition_format.md` §3 allows for x86.
const X86_FAMILIES: &[&str] = &["legacy", "vex", "evex"];

/// Read and check one definition document.
pub fn read(bytes: &[u8]) -> Result<Definition, Diagnostic> {
    let document = json::parse(bytes).map_err(|error| {
        Diagnostic::new(codes::E_DEF_001, "")
            .with("declared", "")
            .with("actual", "")
            .with("reason", error.reason())
    })?;
    bind_document(&document)
}

fn bind_document(document: &json::Json) -> Result<Definition, Diagnostic> {
    let root = Obj::new("", "definition", document).map_err(|fault| fault.definition())?;
    root.closed(DEFINITION_FIELDS)
        .map_err(|fault| fault.definition())?;

    let (format, format_path) = root
        .required("definition_format")
        .map_err(|fault| fault.definition())?;
    let definition_format =
        bind::owned_string(format, format_path).map_err(|fault| fault.definition())?;
    if definition_format != codes::DEFINITION_FORMAT {
        return Err(Diagnostic::new(codes::E_DEF_001, "")
            .with("declared", "")
            .with("actual", "")
            .with(
                "reason",
                format!(
                    "definition_format {definition_format:?} is not {}",
                    codes::DEFINITION_FORMAT
                ),
            ));
    }

    let (namespace, namespace_path) = root
        .required("namespace")
        .map_err(|fault| fault.definition())?;
    let namespace =
        bind::owned_string(namespace, namespace_path).map_err(|fault| fault.definition())?;
    let (version, version_path) = root
        .required("version")
        .map_err(|fault| fault.definition())?;
    let version = bind::owned_string(version, version_path).map_err(|fault| fault.definition())?;

    let target = bind_target(&root)?;
    let forms = bind_forms(&root)?;

    let digest = crate::canonical::canonical_digest(document);
    Ok(Definition {
        document: document.clone(),
        definition_format,
        namespace,
        version,
        target,
        forms,
        digest,
    })
}

fn bind_target(root: &Obj) -> Result<DefinitionTarget, Diagnostic> {
    let (value, path) = root
        .required("target_identity")
        .map_err(|fault| fault.definition())?;
    let obj = Obj::new(path, "target_identity", value).map_err(|fault| fault.definition())?;
    obj.closed(TARGET_FIELDS)
        .map_err(|fault| fault.definition())?;
    let read_string = |field: &str| -> Result<String, Diagnostic> {
        let (value, path) = obj.required(field).map_err(|fault| fault.definition())?;
        bind::owned_string(value, path).map_err(|fault| fault.definition())
    };
    let extensions = {
        let (value, path) = obj
            .required("enabled_extensions")
            .map_err(|fault| fault.definition())?;
        let items = bind::array(value, path.clone()).map_err(|fault| fault.definition())?;
        let mut out = Vec::with_capacity(items.len());
        for (index, item) in items.iter().enumerate() {
            out.push(
                bind::owned_string(item, bind::pointer_index(&path, index))
                    .map_err(|fault| fault.definition())?,
            );
        }
        out
    };
    let address_width = {
        let (value, path) = obj
            .required("address_width")
            .map_err(|fault| fault.definition())?;
        bind::bounded_u32(value, path, u32::MAX, "u32").map_err(|fault| fault.definition())?
    };
    Ok(DefinitionTarget {
        isa_family: read_string("isa_family")?,
        isa_variant: read_string("isa_variant")?,
        execution_mode: read_string("execution_mode")?,
        enabled_extensions: extensions,
        byte_order: read_string("byte_order")?,
        address_width,
    })
}

fn bind_forms(root: &Obj) -> Result<Vec<Form>, Diagnostic> {
    let (value, path) = root.required("forms").map_err(|fault| fault.definition())?;
    let items = bind::array(value, path.clone()).map_err(|fault| fault.definition())?;
    if items.is_empty() {
        return Err(load_error(
            "forms",
            "a definition must declare at least one form",
        ));
    }
    let mut forms: Vec<Form> = Vec::with_capacity(items.len());
    for (index, item) in items.iter().enumerate() {
        let form = bind_form(item, bind::pointer_index(&path, index))?;
        if forms.iter().any(|other| other.form_id == form.form_id) {
            return Err(load_error(
                "duplicate form_id",
                &format!("two rows declare {}", form.form_id),
            ));
        }
        forms.push(form);
    }
    Ok(forms)
}

fn bind_form(value: &json::Json, path: String) -> Result<Form, Diagnostic> {
    let obj = Obj::new(path, "form", value).map_err(|fault| fault.definition())?;
    obj.closed(FORM_FIELDS)
        .map_err(|fault| fault.definition())?;

    let (id, id_path) = obj
        .required("form_id")
        .map_err(|fault| fault.definition())?;
    let form_id = bind::owned_string(id, id_path).map_err(|fault| fault.definition())?;
    check_form_id(&form_id)?;

    let (template, template_path) = obj
        .required("template")
        .map_err(|fault| fault.definition())?;
    let hex = bind::owned_string(template, template_path).map_err(|fault| fault.definition())?;
    let template = decode_hex(&form_id, &hex)?;

    let (slots, slots_path) = obj.required("slots").map_err(|fault| fault.definition())?;
    let items = bind::array(slots, slots_path.clone()).map_err(|fault| fault.definition())?;
    if items.is_empty() {
        return Err(load_error(
            &form_id,
            "a form must declare at least one slot",
        ));
    }
    let bits = (template.len() as u32) * 8;
    let mut slots: Vec<Slot> = Vec::with_capacity(items.len());
    let mut occupied: Vec<Option<usize>> = vec![None; bits as usize];
    for (index, item) in items.iter().enumerate() {
        let slot = bind_slot(item, bind::pointer_index(&slots_path, index))?;
        for (offset, width) in slot.owned_bits() {
            if offset + width > bits {
                return Err(load_error(
                    &form_id,
                    &format!(
                        "slot {index} placement [{offset},{width}] exceeds the {bits}-bit template"
                    ),
                ));
            }
            for bit in offset..offset + width {
                if let Some(owner) = occupied[bit as usize] {
                    return Err(load_error(
                        &form_id,
                        &format!("slot {index} overlaps slot {owner} at bit {bit}"),
                    ));
                }
                occupied[bit as usize] = Some(index);
            }
        }
        slots.push(slot);
    }
    // `ADR-0029`: a REX prefix re-labels 8-bit register numbers 4–7 from
    // `ah`/`ch`/`dh`/`bh` to `spl`/`bpl`/`sil`/`dil`, so the high-byte kind can
    // only sit in a template without a leading REX byte, and a REX-less low-byte
    // slot must not accept 4–7 (they would encode the high bytes instead).
    let rex_prefixed = matches!(template.first(), Some(byte) if (0x40..=0x4f).contains(byte));
    for (index, slot) in slots.iter().enumerate() {
        if slot.kind == "x86.gpr8h" && rex_prefixed {
            return Err(load_error(
                &form_id,
                &format!("slot {index}: a REX-prefixed form cannot carry x86.gpr8h"),
            ));
        }
        if slot.kind == "x86.gpr8"
            && !rex_prefixed
            && ![4, 5, 6, 7]
                .iter()
                .all(|value| slot.excluded.contains(value))
        {
            return Err(load_error(
                &form_id,
                &format!("slot {index}: a REX-less x86.gpr8 slot must exclude 4..=7"),
            ));
        }
    }
    Ok(Form {
        form_id,
        template,
        slots,
    })
}

fn bind_slot(value: &json::Json, path: String) -> Result<Slot, Diagnostic> {
    let obj = Obj::new(path, "slot", value).map_err(|fault| fault.definition())?;
    obj.closed(SLOT_FIELDS)
        .map_err(|fault| fault.definition())?;

    let read_string = |field: &str| -> Result<String, Diagnostic> {
        let (value, path) = obj.required(field).map_err(|fault| fault.definition())?;
        bind::owned_string(value, path).map_err(|fault| fault.definition())
    };

    let role = read_string("role")?;
    if !ROLES.contains(&role.as_str()) {
        return Err(load_error(
            "slot.role",
            &format!("{role:?} is not one of the contract's roles"),
        ));
    }
    let kind = read_string("kind")?;
    let target_type = read_string("target_type")?;

    let (from, _) = obj.required("from").map_err(|fault| fault.definition())?;
    let from = match bind::string(from, obj.child("from")).map_err(|fault| fault.definition())? {
        "reg_number" => SlotFrom::RegNumber,
        "operand_value" => SlotFrom::OperandValue,
        other => {
            return Err(load_error(
                "slot.from",
                &format!("{other:?} is not reg_number or operand_value"),
            ))
        }
    };

    let range = match obj.optional("range") {
        Some((value, path)) => Some(bind_range(value, path)?),
        None => None,
    };
    match (from, range) {
        (SlotFrom::OperandValue, None) => {
            return Err(load_error(
                "slot.range",
                "an operand_value slot must declare a range",
            ))
        }
        (SlotFrom::RegNumber, Some(_)) => {
            return Err(load_error(
                "slot.range",
                "a reg_number slot must not declare a range",
            ))
        }
        _ => {}
    }

    let excluded = match obj.optional("excluded") {
        Some((value, path)) => {
            let items = bind::array(value, path.clone()).map_err(|fault| fault.definition())?;
            if items.is_empty() {
                return Err(load_error(
                    "slot.excluded",
                    "an empty list is not a statement; omit the key instead",
                ));
            }
            let mut out = Vec::with_capacity(items.len());
            for (index, item) in items.iter().enumerate() {
                out.push(
                    bind::integer(item, bind::pointer_index(&path, index))
                        .map_err(|fault| fault.definition())?,
                );
            }
            out
        }
        None => Vec::new(),
    };

    let modifiers = {
        let (value, path) = obj
            .required("modifiers")
            .map_err(|fault| fault.definition())?;
        let items = bind::array(value, path.clone()).map_err(|fault| fault.definition())?;
        let mut out = Vec::with_capacity(items.len());
        for (index, item) in items.iter().enumerate() {
            out.push(bind_modifier(item, bind::pointer_index(&path, index))?);
        }
        out
    };

    let (placements, placements_path) = obj
        .required("placements")
        .map_err(|fault| fault.definition())?;
    let items =
        bind::array(placements, placements_path.clone()).map_err(|fault| fault.definition())?;
    if items.is_empty() {
        return Err(load_error(
            "slot.placements",
            "a slot needs at least one placement",
        ));
    }
    let mut bound = Vec::with_capacity(items.len());
    let mut width_bits = 0u32;
    for (index, item) in items.iter().enumerate() {
        let placement = bind_placement(item, bind::pointer_index(&placements_path, index))?;
        width_bits += placement.width;
        bound.push(placement);
    }
    if let Some(range) = range {
        if width_bits != range.bits {
            return Err(load_error(
                "slot.placements",
                &format!(
                    "placements sum to {width_bits} bits but range.bits is {}",
                    range.bits
                ),
            ));
        }
    }
    // The excluded set is subtracted from the slot's domain, so an entry outside
    // it would be dead weight: it would suggest a rejection that can never
    // happen. Reject it at load time rather than carry a misleading row.
    for (index, value) in excluded.iter().enumerate() {
        if index > 0 && excluded[index - 1] >= *value {
            return Err(load_error(
                "slot.excluded",
                "values must be strictly increasing and unique",
            ));
        }
        let (min, max) = match range {
            Some(range) if range.signed => (
                -(1i128 << (range.bits - 1)),
                (1i128 << (range.bits - 1)) - 1,
            ),
            Some(range) => (0, (1i128 << range.bits) - 1),
            None if width_bits >= 127 => (0, i128::MAX),
            None => (0, (1i128 << width_bits) - 1),
        };
        if *value < min || *value > max {
            return Err(load_error(
                "slot.excluded",
                &format!("{value} is outside the slot's domain [{min}, {max}]"),
            ));
        }
    }
    Ok(Slot {
        role,
        kind,
        target_type,
        from,
        range,
        modifiers,
        placements: bound,
        excluded,
        width_bits,
    })
}

fn bind_range(value: &json::Json, path: String) -> Result<Range, Diagnostic> {
    let obj = Obj::new(path, "range", value).map_err(|fault| fault.definition())?;
    obj.closed(&["signed", "bits", "align_bits"])
        .map_err(|fault| fault.definition())?;
    let (signed, signed_path) = obj.required("signed").map_err(|fault| fault.definition())?;
    let (bits, bits_path) = obj.required("bits").map_err(|fault| fault.definition())?;
    let (align, align_path) = obj
        .required("align_bits")
        .map_err(|fault| fault.definition())?;
    let bits = bind::bounded_u32(bits, bits_path, 64, "u7").map_err(|fault| fault.definition())?;
    if bits == 0 {
        return Err(load_error("slot.range.bits", "must be at least 1"));
    }
    Ok(Range {
        signed: bind::boolean(signed, signed_path).map_err(|fault| fault.definition())?,
        bits,
        align_bits: bind::bounded_u32(align, align_path, 12, "u4")
            .map_err(|fault| fault.definition())?,
    })
}

fn bind_placement(value: &json::Json, path: String) -> Result<Placement, Diagnostic> {
    let obj = Obj::new(path, "placement", value).map_err(|fault| fault.definition())?;
    obj.closed(PLACEMENT_FIELDS)
        .map_err(|fault| fault.definition())?;
    let (offset, offset_path) = obj
        .required("bit_offset")
        .map_err(|fault| fault.definition())?;
    let (width, width_path) = obj.required("width").map_err(|fault| fault.definition())?;
    let width =
        bind::bounded_u32(width, width_path, 64, "u7").map_err(|fault| fault.definition())?;
    if width == 0 {
        return Err(load_error("placement.width", "must be at least 1"));
    }
    Ok(Placement {
        bit_offset: bind::bounded_u32(offset, offset_path, u32::MAX, "u32")
            .map_err(|fault| fault.definition())?,
        width,
    })
}

fn bind_modifier(value: &json::Json, path: String) -> Result<Modifier, Diagnostic> {
    let obj = Obj::new(path, "modifier", value).map_err(|fault| fault.definition())?;
    obj.closed(&["name", "value"])
        .map_err(|fault| fault.definition())?;
    let (name, name_path) = obj.required("name").map_err(|fault| fault.definition())?;
    let (raw, raw_path) = obj.required("value").map_err(|fault| fault.definition())?;
    let value = match raw {
        json::Json::Int(number) => crate::plan::ModifierValue::Int(*number),
        json::Json::Str(text) => crate::plan::ModifierValue::Text(text.clone()),
        json::Json::Bool(flag) => crate::plan::ModifierValue::Bool(*flag),
        other => {
            return Err(load_error(
                "modifier.value",
                &format!(
                    "expected integer, string or boolean, found {}",
                    other.kind()
                ),
            ))
        }
    };
    let _ = raw_path;
    Ok(Modifier {
        name: bind::owned_string(name, name_path).map_err(|fault| fault.definition())?,
        value,
    })
}

fn decode_hex(form_id: &str, text: &str) -> Result<Vec<u8>, Diagnostic> {
    if text.is_empty() {
        return Err(load_error(form_id, "template is empty"));
    }
    if text.len() % 2 != 0 {
        return Err(load_error(
            form_id,
            "template has an odd number of hex digits",
        ));
    }
    let mut out = Vec::with_capacity(text.len() / 2);
    let bytes = text.as_bytes();
    for pair in bytes.chunks(2) {
        let high = hex_digit(pair[0]);
        let low = hex_digit(pair[1]);
        match (high, low) {
            (Some(high), Some(low)) => out.push(high * 16 + low),
            _ => return Err(load_error(form_id, "template is not lowercase hex")),
        }
    }
    Ok(out)
}

fn hex_digit(byte: u8) -> Option<u8> {
    match byte {
        b'0'..=b'9' => Some(byte - b'0'),
        b'a'..=b'f' => Some(byte - b'a' + 10),
        _ => None,
    }
}

/// `01_contract.md` §7: `<family> ":" <mnemonic> "/" <variant>` with an
/// `<encoding_family>` segment required for x86 and forbidden elsewhere.
fn check_form_id(form_id: &str) -> Result<(), Diagnostic> {
    let (family, rest) = match form_id.split_once(':') {
        Some(pair) => pair,
        None => {
            return Err(load_error(
                form_id,
                "form_id is not `<family>:<mnemonic>/<variant>`",
            ))
        }
    };
    if !matches!(family, "x86" | "aarch64" | "riscv") {
        return Err(load_error(form_id, "form_id has an unknown ISA family"));
    }
    let segments: Vec<&str> = rest.split('/').collect();
    if segments.iter().any(|segment| segment.is_empty()) {
        return Err(load_error(form_id, "form_id has an empty component"));
    }
    match family {
        "x86" => {
            if segments.len() != 3 {
                return Err(load_error(
                    form_id,
                    "an x86 form_id needs /legacy, /vex or /evex",
                ));
            }
            if !X86_FAMILIES.contains(&segments[2]) {
                return Err(load_error(
                    form_id,
                    "the encoding family is not legacy, vex or evex",
                ));
            }
        }
        _ => {
            if segments.len() != 2 {
                return Err(load_error(
                    form_id,
                    "an aarch64 or riscv form_id has no encoding family",
                ));
            }
        }
    }
    Ok(())
}

fn load_error(where_: &str, reason: &str) -> Diagnostic {
    Diagnostic::new(codes::E_DEF_001, String::new())
        .with("declared", "")
        .with("actual", "")
        .with("reason", format!("{where_}: {reason}"))
}

/// The set of definitions this materializer can load.
#[derive(Clone, Debug, Default)]
pub struct Registry {
    definitions: Vec<Definition>,
}

impl Registry {
    pub fn new() -> Self {
        Registry::default()
    }

    pub fn add(&mut self, definition: Definition) {
        self.definitions.push(definition);
    }

    pub fn definitions(&self) -> &[Definition] {
        &self.definitions
    }

    /// Read every `*.json` under `dir`, in sorted path order.
    ///
    /// Reads the definition tree on disk; never consulted while encoding, so it
    /// cannot affect bytes beyond which table is selected.
    pub fn load_dir(dir: &Path) -> Result<Self, Diagnostic> {
        let mut paths: Vec<PathBuf> = Vec::new();
        collect_json(dir, &mut paths)?;
        paths.sort();
        let mut registry = Registry::new();
        for path in paths {
            let bytes = std::fs::read(&path).map_err(|error| {
                Diagnostic::new(codes::E_DEF_001, String::new())
                    .with("declared", "")
                    .with("actual", "")
                    .with("reason", format!("{}: {error}", path.display()))
            })?;
            registry.add(read(&bytes)?);
        }
        Ok(registry)
    }

    /// `namespace + version` must name exactly one definition (`01_contract.md`
    /// §5). Absent is `E-DEF-002`.
    pub fn find(&self, namespace: &str, version: &str) -> Result<&Definition, Diagnostic> {
        let matches: Vec<&Definition> = self
            .definitions
            .iter()
            .filter(|definition| definition.namespace == namespace && definition.version == version)
            .collect();
        match matches.as_slice() {
            [definition] => Ok(definition),
            [] => Err(Diagnostic::new(codes::E_DEF_002, "/definition_identity")
                .with("namespace", namespace)
                .with("version", version)),
            _ => Err(Diagnostic::new(codes::E_DEF_001, "/definition_identity")
                .with("declared", format!("{namespace}/{version}"))
                .with("actual", format!("{} definitions", matches.len()))
                .with(
                    "reason",
                    format!("{namespace}/{version} is declared by more than one definition"),
                )),
        }
    }
}

fn collect_json(dir: &Path, out: &mut Vec<PathBuf>) -> Result<(), Diagnostic> {
    let entries = std::fs::read_dir(dir).map_err(|error| {
        Diagnostic::new(codes::E_DEF_001, String::new())
            .with("declared", "")
            .with("actual", "")
            .with("reason", format!("{}: {error}", dir.display()))
    })?;
    for entry in entries {
        let entry = entry.map_err(|error| {
            Diagnostic::new(codes::E_DEF_001, String::new())
                .with("declared", "")
                .with("actual", "")
                .with("reason", format!("{}: {error}", dir.display()))
        })?;
        let path = entry.path();
        if path.is_dir() {
            collect_json(&path, out)?;
        } else if path.extension().and_then(|extension| extension.to_str()) == Some("json") {
            out.push(path);
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn document(form: &str) -> String {
        [
            r#"{"definition_format":"fmp-def/0.1","namespace":"monasm.isa.x86","version":"test","#,
            r#""target_identity":{"isa_family":"x86","isa_variant":"x86-64","execution_mode":"64","#,
            r#""enabled_extensions":[],"byte_order":"little","address_width":64},"forms":["#,
            form,
            "]}",
        ]
        .concat()
    }

    fn form(id: &str, template: &str, slot: &str) -> String {
        format!(r#"{{"form_id":"{id}","template":"{template}","slots":[{slot}]}}"#)
    }

    const HIGH_SLOT: &str = r#"{"role":"dest","kind":"x86.gpr8h","target_type":"rm8h","from":"reg_number","modifiers":[],"placements":[{"bit_offset":16,"width":3}]}"#;
    const LOW_SLOT: &str = r#"{"role":"dest","kind":"x86.gpr8","target_type":"rm8","from":"reg_number","modifiers":[],"placements":[{"bit_offset":8,"width":3}]}"#;

    /// `ADR-0029`: a REX prefix re-labels 4–7 as `spl`/`bpl`/`sil`/`dil`, so a
    /// high-byte slot in a REX form would encode a different register silently.
    #[test]
    fn high_byte_kind_is_rejected_on_a_rex_form() {
        let text = document(&form("x86:mov/rm8h-r8h/legacy", "4088e0", HIGH_SLOT));
        let error = read(text.as_bytes()).expect_err("a REX form must not carry x86.gpr8h");
        assert_eq!(error.code(), codes::E_DEF_001);
        assert!(format!("{error:?}").contains("x86.gpr8h"));
    }

    /// The same rule seen from the other side: without REX, value 4 is `ah`, so a
    /// `x86.gpr8` slot that accepts it would name the wrong register.
    #[test]
    fn low_byte_kind_without_rex_must_exclude_the_high_numbers() {
        let text = document(&form("x86:mov/rm8-r8/legacy", "88c0", LOW_SLOT));
        let error = read(text.as_bytes()).expect_err("a REX-less gpr8 slot must exclude 4..=7");
        assert_eq!(error.code(), codes::E_DEF_001);
        assert!(format!("{error:?}").contains("exclude 4..=7"));
    }
}
