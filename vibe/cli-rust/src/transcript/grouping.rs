//! Which entries render, and the summary of each packed tool group.

use std::collections::HashSet;

use serde_json::Value;

use super::StoredEntry;
use crate::server::{CheckpointEntry, EffectEntry, HistoryEntry, NoticeDetail};

mod label;

pub(crate) const KEY_PREFIX: &str = "tool-group:";

/// Calls per kind in first-seen order.
pub type KindCounts<'a> = Vec<(&'a str, usize)>;

pub struct Group<'a> {
    pub key: String,
    pub first: bool,
    pub last: bool,
    pub finalized: bool,
    /// Settled calls per kind; empty except on the group's first entry.
    pub kinds: KindCounts<'a>,
    /// Calls still running per kind; empty except on the group's first entry.
    pub running: KindCounts<'a>,
    pub reasoning: bool,
    /// Text lines of the group's reasoning traces, so the label can size them.
    pub reasoning_lines: usize,
    /// A reasoning row of the live group is still streaming.
    pub thinking: bool,
    /// Hook lines in the group: the header counts them when it has nothing else.
    pub hooks: usize,
}

impl Group<'_> {
    /// Running calls, then settled ones, then reasoning: `Calling 1 tool, called 2 tools, thought (12 lines)`.
    pub fn label(&self) -> String {
        label::of(self)
    }
}

/// Reasoning, hook notices, and agent effects share one group. A user's `!`
/// command uses the same effect kind as an agent shell call but stays standalone.
pub fn groups_with_tools(entry: &HistoryEntry) -> bool {
    match entry {
        HistoryEntry::Reasoning(_) => true,
        HistoryEntry::Notice(notice) => notice
            .detail
            .as_ref()
            .and_then(|detail| detail.kind.as_deref())
            .is_some_and(|kind| kind.starts_with("hook_")),
        HistoryEntry::Effect(effect) => {
            let Some(detail) = effect.detail.as_ref() else {
                return true;
            };
            detail.tool_name.as_deref() != Some("shell")
                && detail.kind.as_deref() != Some("user_question")
        }
        _ => false,
    }
}

pub fn effect_kind(entry: &HistoryEntry) -> Option<&str> {
    let HistoryEntry::Effect(effect) = entry else {
        return None;
    };
    effect.kind()
}

/// Whether the entry paints no transcript row: a callback (the approval panel
/// is transient), a server notice that only drives side effects (`push_notice`
/// in `ui/transcript/entry/notice.rs` is the dispatch this must mirror), a
/// server checkpoint other than a painted compaction, resume or model change, or an
/// unrecognized type. Such rows must not break a run of tool calls into
/// consecutive blocks: all calls between them collapse into one block.
pub fn renders_nothing(entry: &HistoryEntry, local: bool) -> bool {
    if groups_with_tools(entry) {
        return false;
    }
    match entry {
        HistoryEntry::Callback(_) | HistoryEntry::Unknown => true,
        HistoryEntry::Checkpoint(checkpoint) => {
            !local
                && !(checkpoint.kind == "model_change"
                    || checkpoint.kind == RELOCATION
                    || paints_compaction(checkpoint)
                    || paints_resumed(checkpoint))
        }
        // A fired loop paints on its prompt; goal notices are the only server notices with a row.
        HistoryEntry::Notice(_) => !local && !super::goal_notice::is_goal(entry),
        _ => false,
    }
}

/// The checkpoint a session's move to another folder (`/cd`) leaves in its history.
pub const RELOCATION: &str = "relocation";

/// Whether a server checkpoint paints as a compaction row. `/compact` paints its
/// own local row, so a manual compaction paints none, live or resumed.
pub fn paints_compaction(checkpoint: &CheckpointEntry) -> bool {
    checkpoint.kind == "compaction"
        && checkpoint.details.get("trigger").and_then(Value::as_str) != Some("manual")
}

/// Whether a server checkpoint marks a turn carried on after a restart.
pub fn paints_resumed(checkpoint: &CheckpointEntry) -> bool {
    checkpoint.kind == "resumed"
}

/// Whether a settled compaction checkpoint records a failed attempt.
pub fn compaction_failed(checkpoint: &CheckpointEntry) -> bool {
    checkpoint
        .details
        .get("error")
        .is_some_and(|error| !error.is_null())
}

/// The kind a group counts a call under: unknown or missing kinds share `tool`.
fn label_kind(effect: &EffectEntry) -> &str {
    let kind = batch_kind(effect).or_else(|| effect.kind());
    match kind {
        Some(kind) if label::category(kind).is_some() => kind,
        _ => "tool",
    }
}

/// The kind a batch tool counts as. The server sends it as a generic call with
/// one input holding several targets, so its name is what tells it apart.
fn batch_kind(effect: &EffectEntry) -> Option<&'static str> {
    let name = effect.detail.as_ref()?.tool_name.as_deref()?;
    Some(match name {
        "read_files" | "index" => "file_read",
        "multiedit" => "file_edit",
        "glob" => "file_search",
        _ => return None,
    })
}

/// Kinds in first-seen order, as `(running, settled)`: a call runs while its
/// group is `live` and it has no verdict. File kinds count distinct paths, the
/// rest count calls.
pub(super) fn count_kinds<'a>(
    effects: impl Iterator<Item = &'a EffectEntry>,
    live: bool,
) -> (KindCounts<'a>, KindCounts<'a>) {
    let mut running = KindCounts::new();
    let mut settled = KindCounts::new();
    let mut paths = HashSet::new();
    for effect in effects {
        let kind = match effect.is_model_wait() {
            true => "wait",
            false => label_kind(effect),
        };
        let is_running = live && !effect.is_terminal();
        let kinds = match is_running {
            true => &mut running,
            false => &mut settled,
        };
        let targets = file_paths(kind, effect);
        let adds = match targets.is_empty() {
            true => 1,
            // A batch call counts each of its targets once.
            false => targets
                .into_iter()
                .filter(|path| paths.insert((is_running, kind, *path)))
                .count(),
        };
        match kinds.iter_mut().find(|(seen, _)| *seen == kind) {
            Some((_, count)) => *count += adds,
            None => kinds.push((kind, adds)),
        }
    }
    (running, settled)
}

/// The targets of a call whose kind counts files (`read 2 files`): a batch
/// read lists `paths`, a rename or a batch edit names one path.
fn file_paths<'a>(kind: &str, effect: &'a EffectEntry) -> Vec<&'a str> {
    if !matches!(kind, "file_read" | "file_edit" | "file_write") {
        return Vec::new();
    }
    let Some(input) = effect.input() else {
        return Vec::new();
    };
    for key in ["paths", "filePath", "file_path", "path"] {
        match input.get(key) {
            Some(Value::Array(paths)) => return paths.iter().filter_map(Value::as_str).collect(),
            Some(Value::String(path)) => return vec![path.as_str()],
            _ => {}
        }
    }
    Vec::new()
}

/// Hook lifecycle notices are not rendered inline, except a completed hook with
/// content and a name whose `(scope, toolCallId)` container is still open.
pub(super) fn is_hidden_hook_notice(entry: &HistoryEntry, prior: &[StoredEntry]) -> bool {
    let HistoryEntry::Notice(notice) = entry else {
        return false;
    };
    match notice.detail.as_ref().and_then(|d| d.kind.as_deref()) {
        Some("hook_run_started" | "hook_run_completed" | "hook_started") => true,
        Some("hook_completed") => notice
            .detail
            .as_ref()
            .is_none_or(|d| !hook_line_mounts(d, prior)),
        _ => false,
    }
}

/// A completed hook mounts its system message line only when the
/// content and hook name are set and the `(scope, toolCallId)` container a
/// `hook_run_started` opened is still registered.
fn hook_line_mounts(detail: &NoticeDetail, prior: &[StoredEntry]) -> bool {
    let content = detail.content.as_deref().is_some_and(|c| !c.is_empty());
    let name = detail.hook_name.is_some();
    content && name && container_open(detail, prior)
}

/// The hook container key: a turn-level run keys its scope for the whole
/// turn, the tool-scoped runs key on the tool call id.
fn container_key(detail: &NoticeDetail) -> String {
    match detail.scope.as_deref() {
        Some("post_agent") => "agent_turn".to_owned(),
        Some("pre_agent") => "agent_turn_start".to_owned(),
        Some(scope @ ("pre_llm" | "post_llm")) => scope.to_owned(),
        scope => format!(
            "{}:{}",
            scope.unwrap_or(""),
            detail.tool_call_id.as_deref().unwrap_or("")
        ),
    }
}

/// Whether the key's latest run event is a `hook_run_started`, not a
/// `hook_run_completed` (`_hook_containers` is popped by the run's completion).
fn container_open(detail: &NoticeDetail, prior: &[StoredEntry]) -> bool {
    let key = container_key(detail);
    prior
        .iter()
        .rev()
        .find_map(|stored| {
            let HistoryEntry::Notice(notice) = &stored.typed else {
                return None;
            };
            let prior_detail = notice.detail.as_ref()?;
            let open = match prior_detail.kind.as_deref() {
                Some("hook_run_started") => true,
                Some("hook_run_completed") => false,
                _ => return None,
            };
            (container_key(prior_detail) == key).then_some(open)
        })
        .unwrap_or(false)
}
