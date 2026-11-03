//! The plan model of `docs/fmp-v0/01_contract.md` §3–§11.
//!
//! Binding is structural only. Types, required fields and closed field sets are
//! enforced here, because the typed model cannot represent anything else.
//! Membership in an enum, target agreement, layout validity, operand legality
//! and fixup compatibility are semantic and live in `fmp-validate`, so every one
//! of them is reported with the code the registry assigns rather than a generic
//! parse failure.
//!
//! Every node keeps the JSON Pointer it came from. Diagnostics are only useful
//! if they point at the element the planner wrote.

use crate::bind::{self, Obj};
use crate::codes;
use crate::diagnostic::Diagnostic;
use crate::json;

/// A bound plan plus the document it was read from, so the fingerprint can hash
/// the canonical form of exactly what the planner wrote.
#[derive(Clone, Debug)]
pub struct Plan {
    pub document: json::Json,
    pub format_version: String,
    pub target: TargetIdentity,
    pub definition: DefinitionIdentity,
    pub output: OutputContract,
    pub sections: Vec<Section>,
    pub symbols: Vec<Symbol>,
    pub instructions: Vec<Instruction>,
    pub fixups: Vec<Fixup>,
    pub provenance: Option<Provenance>,
}

#[derive(Clone, Debug)]
pub struct TargetIdentity {
    pub isa_family: String,
    pub isa_variant: String,
    pub execution_mode: String,
    pub enabled_extensions: Vec<String>,
    pub feature_constraints: Vec<String>,
    pub byte_order: String,
    pub address_width: u32,
    pub path: String,
}

#[derive(Clone, Debug)]
pub struct DefinitionIdentity {
    pub namespace: String,
    pub version: String,
    pub digest: String,
    pub source_ref: Option<String>,
    pub path: String,
}

#[derive(Clone, Debug)]
pub struct OutputContract {
    pub artifact: Artifact,
    pub section_order: Vec<String>,
    pub symbol_order: Option<Vec<String>>,
    pub fixup_record_order: String,
    pub include_symbol_table: bool,
    pub emit_fixups: bool,
    pub path: String,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Artifact {
    Bytes,
    Sections,
    Unknown(String),
}

#[derive(Clone, Debug)]
pub struct Section {
    pub section_id: String,
    pub section_kind: SectionKind,
    pub image_backed: bool,
    pub base_address: Option<u64>,
    pub declared_size: u64,
    pub fragments: Vec<Fragment>,
    pub path: String,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum SectionKind {
    Code,
    Data,
    Rodata,
    Bss,
    Unknown(String),
}

#[derive(Clone, Debug)]
pub struct Fragment {
    pub offset: u64,
    pub size: u64,
    pub body: FragmentBody,
    pub path: String,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum FragmentBody {
    Instruction(String),
    Data(String),
    Fill(u8),
}

#[derive(Clone, Debug)]
pub struct Symbol {
    pub symbol_id: String,
    pub name: String,
    pub kind: SymbolKind,
    pub binding: Binding,
    pub section_id: Option<String>,
    pub offset: Option<u64>,
    pub path: String,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum SymbolKind {
    Defined,
    Undefined,
    External,
    Unknown(String),
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Binding {
    Local,
    Global,
    Weak,
    Unknown(String),
}

#[derive(Clone, Debug)]
pub struct Instruction {
    pub instruction_id: String,
    pub section_id: String,
    pub offset: u64,
    pub form_id: String,
    pub operands: Vec<Operand>,
    pub expected_size: u64,
    pub expected_digest: Option<String>,
    pub path: String,
}

#[derive(Clone, Debug)]
pub struct Operand {
    pub role: String,
    pub kind: String,
    pub target_type: String,
    pub payload: Payload,
    pub modifiers: Vec<Modifier>,
    pub path: String,
}

/// The four shapes of `01_contract.md` §8.1.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Payload {
    Register(u64),
    Value(i128),
    Symbol(String),
    Empty,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Modifier {
    pub name: String,
    pub value: ModifierValue,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum ModifierValue {
    Int(i128),
    Text(String),
    Bool(bool),
}

#[derive(Clone, Debug)]
pub struct Fixup {
    pub fixup_id: String,
    pub section_id: String,
    pub offset: u64,
    pub field_descriptor: Vec<FieldRange>,
    pub target: FixupTarget,
    pub addend: i64,
    pub pc_reference_rule: PcRule,
    pub value_transform: Transform,
    pub transform_shift: Option<u32>,
    pub range_constraint: RangeConstraint,
    pub resolution_mode: Mode,
    pub pair_group: Option<String>,
    pub pair_role: Option<PairRole>,
    pub path: String,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct FieldRange {
    pub lsb: u32,
    pub width: u32,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum FixupTarget {
    Symbol(String),
    Absolute(u64),
    SectionRelative(String),
    Unknown(String),
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum PcRule {
    None,
    PcrelBegin,
    PcrelEnd,
    PcrelPage,
    Unknown(String),
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Transform {
    Identity,
    Scale,
    Page,
    Hi20,
    Lo12I,
    Lo12S,
    PcrelHi20,
    Unknown(String),
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Mode {
    ResolveInPlace,
    EmitRelocation,
    Unknown(String),
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum PairRole {
    Hi,
    Lo,
    Unknown(String),
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct RangeConstraint {
    pub signed: bool,
    pub bits: u32,
    pub align_bits: u32,
}

#[derive(Clone, Debug)]
pub struct Provenance {
    pub materializer_version: String,
    pub build_profile: Option<String>,
    pub generated_by: Option<String>,
    pub notes: Option<String>,
    pub path: String,
}

const PLAN_FIELDS: &[&str] = &[
    "format_version",
    "target_identity",
    "definition_identity",
    "output_contract",
    "sections",
    "symbols",
    "instructions",
    "fixups",
    "provenance",
];

/// Read a plan from bytes. `Err` carries the first structural diagnostic; the
/// complete semantic set comes from `fmp_validate`.
pub fn read(bytes: &[u8]) -> Result<Plan, Diagnostic> {
    let document = json::parse(bytes).map_err(|error| match error.fault {
        json::JsonFault::ByteOrderMark => {
            Diagnostic::new(codes::E_PLAN_005, "").with("reason", "byte-order mark")
        }
        json::JsonFault::NonIntegerLiteral(kind) => Diagnostic::new(codes::E_PLAN_002, "")
            .with("path_type", "integer")
            .with("found_kind", kind),
        json::JsonFault::IntegerOverflow => Diagnostic::new(codes::E_PLAN_002, "")
            .with("path_type", "integer")
            .with("found_kind", "out of i128 range"),
        other => {
            let reason = match other {
                json::JsonFault::NotUtf8 => "not valid UTF-8".to_string(),
                json::JsonFault::Syntax(message) => format!("syntax: {message}"),
                json::JsonFault::DuplicateKey(key) => format!("duplicate key: {key}"),
                json::JsonFault::ByteOrderMark
                | json::JsonFault::NonIntegerLiteral(_)
                | json::JsonFault::IntegerOverflow => unreachable!(),
            };
            Diagnostic::new(codes::E_PLAN_004, error.path.clone()).with("reason", reason)
        }
    })?;
    bind(&document)
}

/// Bind a parsed document. Public so a caller that already parsed can avoid a
/// second pass.
pub fn bind(document: &json::Json) -> Result<Plan, Diagnostic> {
    let root = Obj::new("", "plan", document)?;
    root.closed(PLAN_FIELDS)?;

    let (value, path) = root.required("format_version")?;
    let format_version = bind::owned_string(value, path.clone())?;
    if format_version != codes::FORMAT_VERSION {
        return Err(Diagnostic::new(codes::E_PLAN_001, path)
            .with("found", format_version)
            .with("supported", codes::FORMAT_VERSION));
    }

    let target = bind_target(&root)?;
    let definition = bind_definition_identity(&root)?;
    let output = bind_output(&root)?;
    let sections = bind_sections(&root)?;
    let symbols = bind_symbols(&root)?;
    let instructions = bind_instructions(&root)?;
    let fixups = bind_fixups(&root)?;
    let provenance = match root.optional("provenance") {
        Some((value, path)) => Some(bind_provenance(value, path)?),
        None => None,
    };

    Ok(Plan {
        document: document.clone(),
        format_version,
        target,
        definition,
        output,
        sections,
        symbols,
        instructions,
        fixups,
        provenance,
    })
}

const TARGET_FIELDS: &[&str] = &[
    "isa_family",
    "isa_variant",
    "execution_mode",
    "enabled_extensions",
    "feature_constraints",
    "byte_order",
    "address_width",
];

fn bind_target(root: &Obj) -> Result<TargetIdentity, Diagnostic> {
    let (value, path) = root.required("target_identity")?;
    let obj = Obj::new(path.clone(), "target_identity", value)?;
    obj.closed(TARGET_FIELDS)?;
    let (family, family_path) = obj.required("isa_family")?;
    let (variant, variant_path) = obj.required("isa_variant")?;
    let (mode, mode_path) = obj.required("execution_mode")?;
    let (extensions, extensions_path) = obj.required("enabled_extensions")?;
    let (constraints, constraints_path) = obj.required("feature_constraints")?;
    let (byte_order, byte_order_path) = obj.required("byte_order")?;
    let (width, width_path) = obj.required("address_width")?;

    Ok(TargetIdentity {
        isa_family: bind::owned_string(family, family_path)?,
        isa_variant: bind::owned_string(variant, variant_path)?,
        execution_mode: bind::owned_string(mode, mode_path)?,
        enabled_extensions: string_list(extensions, extensions_path)?,
        feature_constraints: string_list(constraints, constraints_path)?,
        byte_order: bind::owned_string(byte_order, byte_order_path)?,
        address_width: bind::bounded_u32(width, width_path, u32::MAX, "u32")?,
        path,
    })
}

const DEFINITION_FIELDS: &[&str] = &["namespace", "version", "digest", "source_ref"];

fn bind_definition_identity(root: &Obj) -> Result<DefinitionIdentity, Diagnostic> {
    let (value, path) = root.required("definition_identity")?;
    let obj = Obj::new(path.clone(), "definition_identity", value)?;
    obj.closed(DEFINITION_FIELDS)?;
    let (namespace, namespace_path) = obj.required("namespace")?;
    let (version, version_path) = obj.required("version")?;
    let (digest, digest_path) = obj.required("digest")?;
    let source_ref = match obj.optional("source_ref") {
        Some((value, path)) => Some(bind::owned_string(value, path)?),
        None => None,
    };
    Ok(DefinitionIdentity {
        namespace: bind::owned_string(namespace, namespace_path)?,
        version: bind::owned_string(version, version_path)?,
        digest: bind::owned_string(digest, digest_path)?,
        source_ref,
        path,
    })
}

const OUTPUT_FIELDS: &[&str] = &[
    "artifact",
    "section_order",
    "symbol_order",
    "fixup_record_order",
    "include_symbol_table",
    "emit_fixups",
];

fn bind_output(root: &Obj) -> Result<OutputContract, Diagnostic> {
    let (value, path) = root.required("output_contract")?;
    let obj = Obj::new(path.clone(), "output_contract", value)?;
    obj.closed(OUTPUT_FIELDS)?;
    let (artifact, _) = obj.required("artifact")?;
    let artifact = match bind::string(artifact, obj.child("artifact"))? {
        "bytes" => Artifact::Bytes,
        "sections" => Artifact::Sections,
        other => Artifact::Unknown(other.to_string()),
    };
    let (order, order_path) = obj.required("section_order")?;
    let section_order = string_list(order, order_path)?;
    let symbol_order = match obj.optional("symbol_order") {
        Some((value, path)) => Some(string_list(value, path)?),
        None => None,
    };
    let (record_order, record_path) = obj.required("fixup_record_order")?;
    let (include, include_path) = obj.required("include_symbol_table")?;
    let (emit, emit_path) = obj.required("emit_fixups")?;
    Ok(OutputContract {
        artifact,
        section_order,
        symbol_order,
        fixup_record_order: bind::owned_string(record_order, record_path)?,
        include_symbol_table: bind::boolean(include, include_path)?,
        emit_fixups: bind::boolean(emit, emit_path)?,
        path,
    })
}

const SECTION_FIELDS: &[&str] = &[
    "section_id",
    "section_kind",
    "image_backed",
    "base_address",
    "declared_size",
    "fragments",
];

fn bind_sections(root: &Obj) -> Result<Vec<Section>, Diagnostic> {
    let (value, path) = root.required("sections")?;
    let items = bind::array(value, path.clone())?;
    let mut sections = Vec::with_capacity(items.len());
    for (index, item) in items.iter().enumerate() {
        sections.push(bind_section(item, bind::pointer_index(&path, index))?);
    }
    Ok(sections)
}

fn bind_section(value: &json::Json, path: String) -> Result<Section, Diagnostic> {
    let obj = Obj::new(path.clone(), "section", value)?;
    obj.closed(SECTION_FIELDS)?;
    let (id, id_path) = obj.required("section_id")?;
    let (kind, kind_path) = obj.required("section_kind")?;
    let (image_backed, image_path) = obj.required("image_backed")?;
    let (declared, declared_path) = obj.required("declared_size")?;
    let (fragments, fragments_path) = obj.required("fragments")?;

    let section_kind = match bind::string(kind, kind_path)? {
        "code" => SectionKind::Code,
        "data" => SectionKind::Data,
        "rodata" => SectionKind::Rodata,
        "bss" => SectionKind::Bss,
        other => SectionKind::Unknown(other.to_string()),
    };
    let base_address = match obj.optional("base_address") {
        Some((value, path)) => Some(bind::u64_in(value, path, "address")?),
        None => None,
    };
    let items = bind::array(fragments, fragments_path.clone())?;
    let mut bound = Vec::with_capacity(items.len());
    for (index, item) in items.iter().enumerate() {
        bound.push(bind_fragment(
            item,
            bind::pointer_index(&fragments_path, index),
        )?);
    }
    Ok(Section {
        section_id: bind::owned_string(id, id_path)?,
        section_kind,
        image_backed: bind::boolean(image_backed, image_path)?,
        base_address,
        declared_size: bind::u64_in(declared, declared_path, "size")?,
        fragments: bound,
        path,
    })
}

fn bind_fragment(value: &json::Json, path: String) -> Result<Fragment, Diagnostic> {
    let obj = Obj::new(path.clone(), "fragment", value)?;
    let (offset, offset_path) = obj.required("offset")?;
    let (size, size_path) = obj.required("size")?;
    let (kind, _) = obj.required("kind")?;
    let kind = bind::string(kind, obj.child("kind"))?;
    let body = match kind {
        "instruction" => {
            obj.closed(&["offset", "size", "kind", "instruction_id"])?;
            let (id, id_path) = obj.required("instruction_id")?;
            FragmentBody::Instruction(bind::owned_string(id, id_path)?)
        }
        "data" => {
            obj.closed(&["offset", "size", "kind", "payload_hex"])?;
            let (hex, hex_path) = obj.required("payload_hex")?;
            let text = bind::owned_string(hex, hex_path)?;
            if text.len() % 2 != 0
                || !text
                    .bytes()
                    .all(|b| b.is_ascii_hexdigit() && !b.is_ascii_uppercase())
            {
                return Err(Diagnostic::new(codes::E_PLAN_002, obj.child("payload_hex"))
                    .with("path_type", "lowercase hex bytes")
                    .with("found_kind", text));
            }
            FragmentBody::Data(text)
        }
        "fill" => {
            obj.closed(&["offset", "size", "kind", "fill_byte"])?;
            let (byte, byte_path) = obj.required("fill_byte")?;
            FragmentBody::Fill(bind::bounded_u32(byte, byte_path, 255, "u8")? as u8)
        }
        other => {
            return Err(Diagnostic::new(codes::E_VERSION_001, obj.child("kind"))
                .with("feature", format!("fragment.kind:{other}"))
                .with("format_version", codes::FORMAT_VERSION))
        }
    };
    Ok(Fragment {
        offset: bind::u64_in(offset, offset_path, "offset")?,
        size: bind::u64_in(size, size_path, "size")?,
        body,
        path,
    })
}

const SYMBOL_FIELDS: &[&str] = &[
    "symbol_id",
    "name",
    "kind",
    "binding",
    "section_id",
    "offset",
    "type",
    "size",
];

fn bind_symbols(root: &Obj) -> Result<Vec<Symbol>, Diagnostic> {
    let (value, path) = root.required("symbols")?;
    let items = bind::array(value, path.clone())?;
    let mut symbols = Vec::with_capacity(items.len());
    for (index, item) in items.iter().enumerate() {
        symbols.push(bind_symbol(item, bind::pointer_index(&path, index))?);
    }
    Ok(symbols)
}

fn bind_symbol(value: &json::Json, path: String) -> Result<Symbol, Diagnostic> {
    let obj = Obj::new(path.clone(), "symbol", value)?;
    obj.closed(SYMBOL_FIELDS)?;
    let (id, id_path) = obj.required("symbol_id")?;
    let (name, name_path) = obj.required("name")?;
    let (kind, kind_path) = obj.required("kind")?;
    let (binding, binding_path) = obj.required("binding")?;
    let kind = match bind::string(kind, kind_path)? {
        "defined" => SymbolKind::Defined,
        "undefined" => SymbolKind::Undefined,
        "external" => SymbolKind::External,
        other => SymbolKind::Unknown(other.to_string()),
    };
    let binding = match bind::string(binding, binding_path)? {
        "local" => Binding::Local,
        "global" => Binding::Global,
        "weak" => Binding::Weak,
        other => Binding::Unknown(other.to_string()),
    };
    let section_id = match obj.optional("section_id") {
        Some((value, path)) => Some(bind::owned_string(value, path)?),
        None => None,
    };
    let offset = match obj.optional("offset") {
        Some((value, path)) => Some(bind::u64_in(value, path, "offset")?),
        None => None,
    };
    Ok(Symbol {
        symbol_id: bind::owned_string(id, id_path)?,
        name: bind::owned_string(name, name_path)?,
        kind,
        binding,
        section_id,
        offset,
        path,
    })
}

const INSTRUCTION_FIELDS: &[&str] = &[
    "instruction_id",
    "section_id",
    "offset",
    "form_id",
    "operands",
    "expected_size",
    "expected_digest",
    "source_trace",
];

fn bind_instructions(root: &Obj) -> Result<Vec<Instruction>, Diagnostic> {
    let (value, path) = root.required("instructions")?;
    let items = bind::array(value, path.clone())?;
    let mut instructions = Vec::with_capacity(items.len());
    for (index, item) in items.iter().enumerate() {
        instructions.push(bind_instruction(item, bind::pointer_index(&path, index))?);
    }
    Ok(instructions)
}

fn bind_instruction(value: &json::Json, path: String) -> Result<Instruction, Diagnostic> {
    let obj = Obj::new(path.clone(), "instruction", value)?;
    obj.closed(INSTRUCTION_FIELDS)?;
    let (id, id_path) = obj.required("instruction_id")?;
    let (section, section_path) = obj.required("section_id")?;
    let (offset, offset_path) = obj.required("offset")?;
    let (form, form_path) = obj.required("form_id")?;
    let (operands, operands_path) = obj.required("operands")?;
    let (size, size_path) = obj.required("expected_size")?;

    let items = bind::array(operands, operands_path.clone())?;
    let mut bound = Vec::with_capacity(items.len());
    for (index, item) in items.iter().enumerate() {
        bound.push(bind_operand(
            item,
            bind::pointer_index(&operands_path, index),
        )?);
    }

    let expected_digest = match obj.optional("expected_digest") {
        Some((value, path)) => Some(bind::owned_string(value, path)?),
        None => None,
    };
    if let Some((value, path)) = obj.optional("source_trace") {
        let trace = Obj::new(path, "source_trace", value)?;
        trace.closed(&["file", "line", "node"])?;
    }

    Ok(Instruction {
        instruction_id: bind::owned_string(id, id_path)?,
        section_id: bind::owned_string(section, section_path)?,
        offset: bind::u64_in(offset, offset_path, "offset")?,
        form_id: bind::owned_string(form, form_path)?,
        operands: bound,
        expected_size: bind::u64_in(size, size_path, "size")?,
        expected_digest,
        path,
    })
}

fn bind_operand(value: &json::Json, path: String) -> Result<Operand, Diagnostic> {
    let obj = Obj::new(path.clone(), "operand", value)?;
    obj.closed(&["role", "kind", "target_type", "payload", "modifiers"])?;
    let (role, role_path) = obj.required("role")?;
    let (kind, kind_path) = obj.required("kind")?;
    let (target_type, target_path) = obj.required("target_type")?;
    let (payload, payload_path) = obj.required("payload")?;
    let (modifiers, modifiers_path) = obj.required("modifiers")?;

    let kind = bind::owned_string(kind, kind_path)?;
    let payload = bind_payload(payload, &payload_path, &kind)?;
    let items = bind::array(modifiers, modifiers_path.clone())?;
    let mut bound = Vec::with_capacity(items.len());
    for (index, item) in items.iter().enumerate() {
        bound.push(bind_modifier(
            item,
            bind::pointer_index(&modifiers_path, index),
        )?);
    }
    Ok(Operand {
        role: bind::owned_string(role, role_path)?,
        kind,
        target_type: bind::owned_string(target_type, target_path)?,
        payload,
        modifiers: bound,
        path,
    })
}

fn bind_payload(value: &json::Json, path: &str, kind: &str) -> Result<Payload, Diagnostic> {
    let entries = match value {
        json::Json::Object(entries) => entries,
        other => {
            return Err(payload_error(
                path,
                kind,
                format!("payload must be an object, found {}", other.kind()),
            ))
        }
    };
    let mut register: Option<u64> = None;
    let mut number: Option<i128> = None;
    let mut symbol: Option<String> = None;
    for (key, item) in entries {
        match key.as_str() {
            "reg" => {
                register = Some(bind::u64_in(item, bind::pointer(path, "reg"), "u64")?);
            }
            "value" => {
                number = Some(bind::integer(item, bind::pointer(path, "value"))?);
            }
            "symbol_id" => {
                symbol = Some(bind::owned_string(item, bind::pointer(path, "symbol_id"))?);
            }
            other => {
                return Err(payload_error(
                    path,
                    kind,
                    format!("unknown payload field `{other}`"),
                ))
            }
        }
    }
    let present = register.is_some() as u8 + number.is_some() as u8 + symbol.is_some() as u8;
    if present > 1 {
        return Err(payload_error(
            path,
            kind,
            "payload states more than one of reg, value, symbol_id",
        ));
    }
    Ok(match (register, number, symbol) {
        (Some(register), _, _) => Payload::Register(register),
        (_, Some(number), _) => Payload::Value(number),
        (_, _, Some(symbol)) => Payload::Symbol(symbol),
        _ => Payload::Empty,
    })
}

fn payload_error(path: &str, kind: &str, reason: impl Into<String>) -> Diagnostic {
    Diagnostic::new(codes::E_OPERAND_003, path.to_string())
        .with("kind", kind.to_string())
        .with("reason", reason.into())
}

fn bind_modifier(value: &json::Json, path: String) -> Result<Modifier, Diagnostic> {
    let obj = Obj::new(path.clone(), "modifier", value)?;
    obj.closed(&["name", "value"])?;
    let (name, name_path) = obj.required("name")?;
    let (raw, raw_path) = obj.required("value")?;
    let value = match raw {
        json::Json::Int(number) => ModifierValue::Int(*number),
        json::Json::Str(text) => ModifierValue::Text(text.clone()),
        json::Json::Bool(flag) => ModifierValue::Bool(*flag),
        other => {
            return Err(Diagnostic::new(codes::E_OPERAND_003, raw_path)
                .with("kind", "modifier")
                .with(
                    "reason",
                    format!(
                        "value must be an integer, string or boolean, found {}",
                        other.kind()
                    ),
                ))
        }
    };
    Ok(Modifier {
        name: bind::owned_string(name, name_path)?,
        value,
    })
}

const FIXUP_FIELDS: &[&str] = &[
    "fixup_id",
    "section_id",
    "offset",
    "field_descriptor",
    "target",
    "addend",
    "pc_reference_rule",
    "value_transform",
    "transform_shift",
    "range_constraint",
    "resolution_mode",
    "pair_group",
    "pair_role",
];

fn bind_fixups(root: &Obj) -> Result<Vec<Fixup>, Diagnostic> {
    let (value, path) = root.required("fixups")?;
    let items = bind::array(value, path.clone())?;
    let mut fixups = Vec::with_capacity(items.len());
    for (index, item) in items.iter().enumerate() {
        fixups.push(bind_fixup(item, bind::pointer_index(&path, index))?);
    }
    Ok(fixups)
}

fn bind_fixup(value: &json::Json, path: String) -> Result<Fixup, Diagnostic> {
    let obj = Obj::new(path.clone(), "fixup", value)?;
    obj.closed(FIXUP_FIELDS)?;
    let (id, id_path) = obj.required("fixup_id")?;
    let (section, section_path) = obj.required("section_id")?;
    let (offset, offset_path) = obj.required("offset")?;
    let (descriptor, descriptor_path) = obj.required("field_descriptor")?;
    let (target, target_path) = obj.required("target")?;
    let (addend, addend_path) = obj.required("addend")?;
    let (rule, _) = obj.required("pc_reference_rule")?;
    let (transform, _) = obj.required("value_transform")?;
    let (constraint, constraint_path) = obj.required("range_constraint")?;
    let (mode, _) = obj.required("resolution_mode")?;

    let descriptor_items = bind::array(descriptor, descriptor_path.clone())?;
    let mut field_descriptor = Vec::with_capacity(descriptor_items.len());
    for (index, item) in descriptor_items.iter().enumerate() {
        field_descriptor.push(bind_field_range(
            item,
            bind::pointer_index(&descriptor_path, index),
        )?);
    }

    let rule = match bind::string(rule, obj.child("pc_reference_rule"))? {
        "none" => PcRule::None,
        "pcrel_begin" => PcRule::PcrelBegin,
        "pcrel_end" => PcRule::PcrelEnd,
        "pcrel_page" => PcRule::PcrelPage,
        other => PcRule::Unknown(other.to_string()),
    };
    let transform = match bind::string(transform, obj.child("value_transform"))? {
        "identity" => Transform::Identity,
        "scale" => Transform::Scale,
        "page" => Transform::Page,
        "hi20" => Transform::Hi20,
        "lo12_i" => Transform::Lo12I,
        "lo12_s" => Transform::Lo12S,
        "pcrel_hi20" => Transform::PcrelHi20,
        other => Transform::Unknown(other.to_string()),
    };
    let mode = match bind::string(mode, obj.child("resolution_mode"))? {
        "resolve_in_place" => Mode::ResolveInPlace,
        "emit_relocation" => Mode::EmitRelocation,
        other => Mode::Unknown(other.to_string()),
    };
    let pair_role = match obj.optional("pair_role") {
        Some((value, path)) => Some(match bind::string(value, path)? {
            "hi" => PairRole::Hi,
            "lo" => PairRole::Lo,
            other => PairRole::Unknown(other.to_string()),
        }),
        None => None,
    };
    let transform_shift = match obj.optional("transform_shift") {
        Some((value, path)) => Some(bind::bounded_u32(value, path, 63, "u6")?),
        None => None,
    };
    let pair_group = match obj.optional("pair_group") {
        Some((value, path)) => Some(bind::owned_string(value, path)?),
        None => None,
    };

    Ok(Fixup {
        fixup_id: bind::owned_string(id, id_path)?,
        section_id: bind::owned_string(section, section_path)?,
        offset: bind::u64_in(offset, offset_path, "offset")?,
        field_descriptor,
        target: bind_target_ref(target, target_path)?,
        addend: bind::i64_in(addend, addend_path, "i64")?,
        pc_reference_rule: rule,
        value_transform: transform,
        transform_shift,
        range_constraint: bind_range_constraint(constraint, constraint_path)?,
        resolution_mode: mode,
        pair_group,
        pair_role,
        path,
    })
}

fn bind_target_ref(value: &json::Json, path: String) -> Result<FixupTarget, Diagnostic> {
    let obj = Obj::new(path.clone(), "fixup.target", value)?;
    let (kind, _) = obj.required("kind")?;
    let kind = bind::string(kind, obj.child("kind"))?.to_string();
    match kind.as_str() {
        "symbol" => {
            obj.closed(&["kind", "symbol_id"])?;
            let (symbol, symbol_path) = obj.required("symbol_id")?;
            Ok(FixupTarget::Symbol(bind::owned_string(
                symbol,
                symbol_path,
            )?))
        }
        "absolute" => {
            obj.closed(&["kind", "address"])?;
            let (address, address_path) = obj.required("address")?;
            Ok(FixupTarget::Absolute(bind::u64_in(
                address,
                address_path,
                "address",
            )?))
        }
        "section_relative" => {
            obj.closed(&["kind", "section_id"])?;
            let (section, section_path) = obj.required("section_id")?;
            Ok(FixupTarget::SectionRelative(bind::owned_string(
                section,
                section_path,
            )?))
        }
        other => {
            obj.closed(&["kind"])?;
            Ok(FixupTarget::Unknown(other.to_string()))
        }
    }
}

fn bind_field_range(value: &json::Json, path: String) -> Result<FieldRange, Diagnostic> {
    let obj = Obj::new(path.clone(), "field_range", value)?;
    obj.closed(&["lsb", "width"])?;
    let (lsb, lsb_path) = obj.required("lsb")?;
    let (width, width_path) = obj.required("width")?;
    Ok(FieldRange {
        lsb: bind::bounded_u32(lsb, lsb_path, 127, "u7")?,
        width: bind::bounded_u32(width, width_path, 64, "u7")?,
    })
}

fn bind_range_constraint(value: &json::Json, path: String) -> Result<RangeConstraint, Diagnostic> {
    let obj = Obj::new(path.clone(), "range_constraint", value)?;
    obj.closed(&["signed", "bits", "align_bits"])?;
    let (signed, signed_path) = obj.required("signed")?;
    let (bits, bits_path) = obj.required("bits")?;
    let (align, align_path) = obj.required("align_bits")?;
    Ok(RangeConstraint {
        signed: bind::boolean(signed, signed_path)?,
        bits: bind::bounded_u32(bits, bits_path, 64, "u7")?,
        align_bits: bind::bounded_u32(align, align_path, 12, "u4")?,
    })
}

const PROVENANCE_FIELDS: &[&str] = &[
    "materializer_version",
    "build_profile",
    "generated_by",
    "notes",
];

fn bind_provenance(value: &json::Json, path: String) -> Result<Provenance, Diagnostic> {
    let obj = Obj::new(path.clone(), "provenance", value)?;
    obj.closed(PROVENANCE_FIELDS)?;
    let (version, version_path) = obj.required("materializer_version")?;
    let optional = |field: &str| -> Result<Option<String>, Diagnostic> {
        match obj.optional(field) {
            Some((value, path)) => Ok(Some(bind::owned_string(value, path)?)),
            None => Ok(None),
        }
    };
    Ok(Provenance {
        materializer_version: bind::owned_string(version, version_path)?,
        build_profile: optional("build_profile")?,
        generated_by: optional("generated_by")?,
        notes: optional("notes")?,
        path,
    })
}

fn string_list(value: &json::Json, path: String) -> Result<Vec<String>, Diagnostic> {
    let items = bind::array(value, path.clone())?;
    let mut out = Vec::with_capacity(items.len());
    for (index, item) in items.iter().enumerate() {
        out.push(bind::owned_string(item, bind::pointer_index(&path, index))?);
    }
    Ok(out)
}
