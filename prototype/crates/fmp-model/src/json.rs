//! A strict JSON reader.
//!
//! `serde_json` is not used for parsing because three of its behaviours are
//! exactly the ones the contract forbids:
//!
//! - it resolves a duplicate key by keeping the last one, silently;
//! - it accepts `1.0` and `1e3` as numbers;
//! - its error text is free-form, so mapping a failure onto a registry code
//!   would depend on the crate's prose.
//!
//! The reader below keeps object members in document order (a plan's list order
//! is observable), rejects duplicate keys at the point they appear, and produces
//! a [`JsonError`] carrying a JSON Pointer so `pytest`-style code mapping is not
//! needed.

/// A JSON value. Integers are `i128`: the widest domain any `fmp/0.1` field
/// needs is `u64`, and an intermediate fit check is done by the binder.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Json {
    Null,
    Bool(bool),
    Int(i128),
    Str(String),
    Array(Vec<Json>),
    Object(Vec<(String, Json)>),
}

impl Json {
    /// The JSON type name, as it appears in a diagnostic.
    pub fn kind(&self) -> &'static str {
        match self {
            Json::Null => "null",
            Json::Bool(_) => "boolean",
            Json::Int(_) => "integer",
            Json::Str(_) => "string",
            Json::Array(_) => "array",
            Json::Object(_) => "object",
        }
    }

    pub fn as_object(&self) -> Option<&[(String, Json)]> {
        match self {
            Json::Object(entries) => Some(entries),
            _ => None,
        }
    }

    pub fn as_array(&self) -> Option<&[Json]> {
        match self {
            Json::Array(items) => Some(items),
            _ => None,
        }
    }

    pub fn as_str(&self) -> Option<&str> {
        match self {
            Json::Str(text) => Some(text),
            _ => None,
        }
    }

    pub fn as_i128(&self) -> Option<i128> {
        match self {
            Json::Int(value) => Some(*value),
            _ => None,
        }
    }

    pub fn as_bool(&self) -> Option<bool> {
        match self {
            Json::Bool(value) => Some(*value),
            _ => None,
        }
    }

    /// Look up a member of an object. `None` for a non-object, so callers decide
    /// whether that is a type fault (it always is, at bind time).
    pub fn get(&self, key: &str) -> Option<&Json> {
        self.as_object()?
            .iter()
            .find(|(name, _)| name == key)
            .map(|(_, value)| value)
    }
}

/// What went wrong, independent of which document was being read.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum JsonFault {
    /// A UTF-8 BOM precedes the document (`E-PLAN-005`).
    ByteOrderMark,
    /// The bytes are not valid UTF-8 (`E-PLAN-004`).
    NotUtf8,
    /// Grammar violation; the payload is a short description.
    Syntax(String),
    /// The same key appeared twice in one object (`E-PLAN-004`).
    DuplicateKey(String),
    /// A number with a fraction or an exponent (`E-PLAN-002`).
    NonIntegerLiteral(&'static str),
    /// An integer literal that does not fit `i128` (`E-PLAN-002`).
    IntegerOverflow,
}

/// A parse failure with the JSON Pointer of the value being read.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct JsonError {
    pub path: String,
    pub fault: JsonFault,
}

impl JsonError {
    /// A short description for a diagnostic's `reason` detail.
    pub fn reason(&self) -> String {
        match &self.fault {
            JsonFault::ByteOrderMark => "byte-order mark".to_string(),
            JsonFault::NotUtf8 => "not valid UTF-8".to_string(),
            JsonFault::Syntax(message) => format!("syntax: {message}"),
            JsonFault::DuplicateKey(key) => format!("duplicate key: {key}"),
            JsonFault::NonIntegerLiteral(kind) => format!("non-integer number: {kind}"),
            JsonFault::IntegerOverflow => "integer does not fit i128".to_string(),
        }
    }
}

/// Read a JSON document.
pub fn parse(bytes: &[u8]) -> Result<Json, JsonError> {
    if bytes.starts_with(&[0xEF, 0xBB, 0xBF]) {
        return Err(JsonError {
            path: String::new(),
            fault: JsonFault::ByteOrderMark,
        });
    }
    let text = std::str::from_utf8(bytes).map_err(|_| JsonError {
        path: String::new(),
        fault: JsonFault::NotUtf8,
    })?;
    let mut parser = Parser {
        src: text.as_bytes(),
        pos: 0,
        path: Vec::new(),
    };
    let value = parser.value()?;
    parser.skip_ws();
    if parser.pos != parser.src.len() {
        return Err(parser.syntax("trailing data after the document"));
    }
    Ok(value)
}

#[derive(Clone)]
enum Segment {
    Key(String),
    Index(usize),
}

struct Parser<'a> {
    src: &'a [u8],
    pos: usize,
    path: Vec<Segment>,
}

impl<'a> Parser<'a> {
    fn pointer(&self) -> String {
        let mut out = String::new();
        for segment in &self.path {
            out.push('/');
            match segment {
                Segment::Index(index) => out.push_str(&index.to_string()),
                Segment::Key(key) => {
                    for ch in key.chars() {
                        match ch {
                            '~' => out.push_str("~0"),
                            '/' => out.push_str("~1"),
                            other => out.push(other),
                        }
                    }
                }
            }
        }
        out
    }

    fn err(&self, fault: JsonFault) -> JsonError {
        JsonError {
            path: self.pointer(),
            fault,
        }
    }

    fn syntax(&self, message: impl Into<String>) -> JsonError {
        self.err(JsonFault::Syntax(message.into()))
    }

    fn peek(&self) -> Option<u8> {
        self.src.get(self.pos).copied()
    }

    fn skip_ws(&mut self) {
        while let Some(byte) = self.peek() {
            match byte {
                b' ' | b'\t' | b'\n' | b'\r' => self.pos += 1,
                _ => break,
            }
        }
    }

    fn expect(&mut self, byte: u8) -> Result<(), JsonError> {
        if self.peek() == Some(byte) {
            self.pos += 1;
            Ok(())
        } else {
            Err(self.syntax(format!("expected `{}`", byte as char)))
        }
    }

    fn value(&mut self) -> Result<Json, JsonError> {
        self.skip_ws();
        match self.peek() {
            None => Err(self.syntax("unexpected end of document")),
            Some(b'{') => self.object(),
            Some(b'[') => self.array(),
            Some(b'"') => Ok(Json::Str(self.string()?)),
            Some(b't') => {
                self.keyword("true")?;
                Ok(Json::Bool(true))
            }
            Some(b'f') => {
                self.keyword("false")?;
                Ok(Json::Bool(false))
            }
            Some(b'n') => {
                self.keyword("null")?;
                Ok(Json::Null)
            }
            Some(b'-') | Some(b'0'..=b'9') => self.number(),
            Some(other) => Err(self.syntax(format!("unexpected byte 0x{other:02x}"))),
        }
    }

    fn object(&mut self) -> Result<Json, JsonError> {
        self.expect(b'{')?;
        let mut entries: Vec<(String, Json)> = Vec::new();
        self.skip_ws();
        if self.peek() == Some(b'}') {
            self.pos += 1;
            return Ok(Json::Object(entries));
        }
        loop {
            self.skip_ws();
            if self.peek() != Some(b'"') {
                return Err(self.syntax("object key must be a string"));
            }
            let key = self.string()?;
            self.skip_ws();
            self.expect(b':')?;
            if entries.iter().any(|(name, _)| *name == key) {
                return Err(self.err(JsonFault::DuplicateKey(key)));
            }
            self.path.push(Segment::Key(key.clone()));
            let value = self.value();
            self.path.pop();
            entries.push((key, value?));
            self.skip_ws();
            match self.peek() {
                Some(b',') => self.pos += 1,
                Some(b'}') => {
                    self.pos += 1;
                    return Ok(Json::Object(entries));
                }
                _ => return Err(self.syntax("expected `,` or `}`")),
            }
        }
    }

    fn array(&mut self) -> Result<Json, JsonError> {
        self.expect(b'[')?;
        let mut items: Vec<Json> = Vec::new();
        self.skip_ws();
        if self.peek() == Some(b']') {
            self.pos += 1;
            return Ok(Json::Array(items));
        }
        loop {
            self.path.push(Segment::Index(items.len()));
            let value = self.value();
            self.path.pop();
            items.push(value?);
            self.skip_ws();
            match self.peek() {
                Some(b',') => self.pos += 1,
                Some(b']') => {
                    self.pos += 1;
                    return Ok(Json::Array(items));
                }
                _ => return Err(self.syntax("expected `,` or `]`")),
            }
        }
    }

    fn keyword(&mut self, word: &str) -> Result<(), JsonError> {
        let bytes = word.as_bytes();
        let end = self.pos + bytes.len();
        if end <= self.src.len() && &self.src[self.pos..end] == bytes {
            self.pos = end;
            Ok(())
        } else {
            Err(self.syntax(format!("expected `{word}`")))
        }
    }

    fn string(&mut self) -> Result<String, JsonError> {
        self.expect(b'"')?;
        let mut out = String::new();
        loop {
            let byte = match self.peek() {
                Some(byte) => byte,
                None => return Err(self.syntax("unterminated string")),
            };
            match byte {
                b'"' => {
                    self.pos += 1;
                    return Ok(out);
                }
                b'\\' => {
                    self.pos += 1;
                    let escape = match self.peek() {
                        Some(escape) => escape,
                        None => return Err(self.syntax("unterminated escape")),
                    };
                    self.pos += 1;
                    match escape {
                        b'"' => out.push('"'),
                        b'\\' => out.push('\\'),
                        b'/' => out.push('/'),
                        b'b' => out.push('\u{8}'),
                        b'f' => out.push('\u{c}'),
                        b'n' => out.push('\n'),
                        b'r' => out.push('\r'),
                        b't' => out.push('\t'),
                        b'u' => {
                            let scalar = self.unicode_escape()?;
                            out.push(scalar);
                        }
                        _ => return Err(self.syntax("unknown escape")),
                    }
                }
                0x00..=0x1F => return Err(self.syntax("raw control character in string")),
                _ => {
                    let start = self.pos;
                    let len = utf8_len(byte);
                    self.pos += len;
                    match std::str::from_utf8(&self.src[start..self.pos]) {
                        Ok(chunk) => out.push_str(chunk),
                        Err(_) => return Err(self.syntax("invalid UTF-8 in string")),
                    }
                }
            }
        }
    }

    fn unicode_escape(&mut self) -> Result<char, JsonError> {
        let high = self.hex4()?;
        let code = if (0xD800..0xDC00).contains(&high) {
            if self.peek() != Some(b'\\') {
                return Err(self.syntax("lone high surrogate"));
            }
            self.pos += 1;
            if self.peek() != Some(b'u') {
                return Err(self.syntax("lone high surrogate"));
            }
            self.pos += 1;
            let low = self.hex4()?;
            if !(0xDC00..0xE000).contains(&low) {
                return Err(self.syntax("invalid low surrogate"));
            }
            0x1_0000 + ((high - 0xD800) << 10) + (low - 0xDC00)
        } else if (0xDC00..0xE000).contains(&high) {
            return Err(self.syntax("lone low surrogate"));
        } else {
            high
        };
        char::from_u32(code).ok_or_else(|| self.syntax("invalid code point"))
    }

    fn hex4(&mut self) -> Result<u32, JsonError> {
        let mut value = 0u32;
        for _ in 0..4 {
            let byte = match self.peek() {
                Some(byte) => byte,
                None => return Err(self.syntax("truncated \\u escape")),
            };
            self.pos += 1;
            let digit = match byte {
                b'0'..=b'9' => (byte - b'0') as u32,
                b'a'..=b'f' => (byte - b'a' + 10) as u32,
                b'A'..=b'F' => (byte - b'A' + 10) as u32,
                _ => return Err(self.syntax("non-hex digit in \\u escape")),
            };
            value = value * 16 + digit;
        }
        Ok(value)
    }

    fn number(&mut self) -> Result<Json, JsonError> {
        let start = self.pos;
        if self.peek() == Some(b'-') {
            self.pos += 1;
        }
        match self.peek() {
            Some(b'0') => self.pos += 1,
            Some(b'1'..=b'9') => {
                while matches!(self.peek(), Some(b'0'..=b'9')) {
                    self.pos += 1;
                }
            }
            _ => return Err(self.syntax("expected a digit")),
        }
        let mut kind: Option<&'static str> = None;
        if self.peek() == Some(b'.') {
            kind = Some("float");
            self.pos += 1;
            if !matches!(self.peek(), Some(b'0'..=b'9')) {
                return Err(self.syntax("digit expected after the decimal point"));
            }
            while matches!(self.peek(), Some(b'0'..=b'9')) {
                self.pos += 1;
            }
        }
        if matches!(self.peek(), Some(b'e') | Some(b'E')) {
            kind = Some("exponent");
            self.pos += 1;
            if matches!(self.peek(), Some(b'+') | Some(b'-')) {
                self.pos += 1;
            }
            if !matches!(self.peek(), Some(b'0'..=b'9')) {
                return Err(self.syntax("digit expected in the exponent"));
            }
            while matches!(self.peek(), Some(b'0'..=b'9')) {
                self.pos += 1;
            }
        }
        if let Some(kind) = kind {
            return Err(self.err(JsonFault::NonIntegerLiteral(kind)));
        }
        let text = std::str::from_utf8(&self.src[start..self.pos])
            .map_err(|_| self.syntax("invalid UTF-8 in number"))?;
        match text.parse::<i128>() {
            Ok(value) => Ok(Json::Int(value)),
            Err(_) => Err(self.err(JsonFault::IntegerOverflow)),
        }
    }
}

fn utf8_len(byte: u8) -> usize {
    match byte {
        0x00..=0x7F => 1,
        0xC0..=0xDF => 2,
        0xE0..=0xEF => 3,
        0xF0..=0xF7 => 4,
        // A continuation byte or an invalid lead: consume one and let
        // `from_utf8` reject the slice.
        _ => 1,
    }
}

/// Pretty-print a value for human consumption, preserving member order.
///
/// Two-space indent, `\n` between lines, no trailing newline. Deterministic by
/// construction: the caller builds the value in a fixed member order, so this
/// never sorts or reorders.
pub fn pretty(value: &Json) -> String {
    let mut out = String::new();
    write_pretty(value, 0, &mut out);
    out
}

fn write_pretty(value: &Json, depth: usize, out: &mut String) {
    match value {
        Json::Array(items) if !items.is_empty() => {
            out.push_str("[\n");
            for (index, item) in items.iter().enumerate() {
                indent(depth + 1, out);
                write_pretty(item, depth + 1, out);
                if index + 1 < items.len() {
                    out.push(',');
                }
                out.push('\n');
            }
            indent(depth, out);
            out.push(']');
        }
        Json::Object(entries) if !entries.is_empty() => {
            out.push_str("{\n");
            for (index, (key, item)) in entries.iter().enumerate() {
                indent(depth + 1, out);
                out.push_str(&quote(key));
                out.push_str(": ");
                write_pretty(item, depth + 1, out);
                if index + 1 < entries.len() {
                    out.push(',');
                }
                out.push('\n');
            }
            indent(depth, out);
            out.push('}');
        }
        Json::Array(_) => out.push_str("[]"),
        Json::Object(_) => out.push_str("{}"),
        Json::Null => out.push_str("null"),
        Json::Bool(true) => out.push_str("true"),
        Json::Bool(false) => out.push_str("false"),
        Json::Int(number) => out.push_str(&number.to_string()),
        Json::Str(text) => out.push_str(&quote(text)),
    }
}

fn indent(depth: usize, out: &mut String) {
    for _ in 0..depth {
        out.push_str("  ");
    }
}

fn quote(text: &str) -> String {
    let mut bytes = Vec::new();
    crate::canonical::write_string(text, &mut bytes);
    String::from_utf8(bytes).expect("escaping produces valid UTF-8")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn reads_nested_values() {
        let json = parse(br#"{"a":[1,{"b":-2}],"c":true,"d":null}"#).unwrap();
        assert_eq!(json.get("c").unwrap().as_bool(), Some(true));
        let array = json.get("a").unwrap().as_array().unwrap();
        assert_eq!(array[0].as_i128(), Some(1));
        assert_eq!(array[1].get("b").unwrap().as_i128(), Some(-2));
    }

    #[test]
    fn rejects_duplicate_keys() {
        let error = parse(br#"{"a":1,"a":2}"#).unwrap_err();
        assert_eq!(error.fault, JsonFault::DuplicateKey("a".to_string()));
        assert_eq!(error.path, "");
    }

    #[test]
    fn rejects_floats_and_exponents() {
        assert_eq!(
            parse(b"1.0").unwrap_err().fault,
            JsonFault::NonIntegerLiteral("float")
        );
        assert_eq!(
            parse(b"1e3").unwrap_err().fault,
            JsonFault::NonIntegerLiteral("exponent")
        );
    }

    #[test]
    fn rejects_a_byte_order_mark() {
        let mut bytes = vec![0xEF, 0xBB, 0xBF];
        bytes.extend_from_slice(b"{}");
        assert_eq!(parse(&bytes).unwrap_err().fault, JsonFault::ByteOrderMark);
    }

    #[test]
    fn reports_a_pointer() {
        let error = parse(br#"{"instructions":[{"offset":1.5}]}"#).unwrap_err();
        assert_eq!(error.path, "/instructions/0/offset");
    }

    #[test]
    fn decodes_escapes_and_surrogates() {
        let json = parse(br#""\u00e9\uD83D\uDE00\n""#).unwrap();
        assert_eq!(json.as_str(), Some("\u{e9}\u{1F600}\n"));
    }

    #[test]
    fn keeps_member_order() {
        let json = parse(br#"{"b":1,"a":2}"#).unwrap();
        let keys: Vec<&str> = json
            .as_object()
            .unwrap()
            .iter()
            .map(|(key, _)| key.as_str())
            .collect();
        assert_eq!(keys, vec!["b", "a"]);
    }

    #[test]
    fn rejects_a_negative_zero_fraction() {
        assert!(parse(b"-0").is_ok());
        assert!(parse(b"-0.0").is_err());
    }
}
