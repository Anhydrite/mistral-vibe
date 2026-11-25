//! The wording of a packed group's summary: `Read 2 files, thought (12 lines)`.

use super::Group;

pub(super) fn of(group: &Group<'_>) -> String {
    let mut labels = segments(&group.running, true);
    labels.extend(segments(&group.kinds, false));
    if group.reasoning {
        labels.push(reasoning_segment(group.thinking, group.reasoning_lines));
    }
    // Model-call hooks can line up with no tool between them.
    if labels.is_empty() && group.hooks > 0 {
        let noun = if group.hooks == 1 { "hook" } else { "hooks" };
        let verb = if group.finalized { "ran" } else { "running" };
        labels.push(format!("{verb} {} {noun}", group.hooks));
    }
    let mut label = labels.join(", ");
    if let Some(first) = label.get_mut(0..1) {
        first.make_ascii_uppercase();
    }
    label
}

/// Kinds sharing a verb merge into one segment: `ran 2 commands and 1 search`.
/// A wait reads as what the agent does, not as a counted call. The main view
/// hides a running one behind the waiting status line; a subagent's view
/// shows it, so it reads as still waiting there.
fn segments(kinds: &[(&str, usize)], running: bool) -> Vec<String> {
    let mut verbs: Vec<(String, Vec<String>)> = Vec::new();
    for &(kind, count) in kinds {
        if let Some(phrase) = uncounted(kind, running) {
            verbs.push((phrase.to_owned(), Vec::new()));
            continue;
        }
        let (verb, noun) = category_terms(kind, count, running);
        let counted = format!("{count} {noun}");
        match verbs.iter_mut().find(|(seen, _)| seen == verb) {
            Some((_, nouns)) => nouns.push(counted),
            None => verbs.push((verb.to_owned(), vec![counted])),
        }
    }
    verbs
        .into_iter()
        .map(|(verb, nouns)| match nouns.is_empty() {
            true => verb,
            false => format!("{verb} {}", join_and(&nouns)),
        })
        .collect()
}

/// The whole segment of a kind that reads without a count.
fn uncounted(kind: &str, running: bool) -> Option<&'static str> {
    (kind == "wait").then_some(match running {
        true => "waiting for background work",
        false => "waited for background work",
    })
}

/// The reasoning segment, sized like the trace row it stands for: `thought (12 lines)`.
fn reasoning_segment(thinking: bool, lines: usize) -> String {
    let verb = if thinking { "thinking" } else { "thought" };
    match lines {
        0 => verb.to_owned(),
        lines => {
            let noun = if lines == 1 { "line" } else { "lines" };
            format!("{verb} ({lines} {noun})")
        }
    }
}

/// The verb and noun of `{verb} {count} {noun}`, e.g. `read 10 files`.
fn category_terms(kind: &str, count: usize, running: bool) -> (&'static str, &'static str) {
    let (done, active, one, many) =
        category(kind).unwrap_or(("called", "calling", "tool", "tools"));
    let verb = if running { active } else { done };
    let noun = if count == 1 { one } else { many };
    (verb, noun)
}

/// `a`, `a and b`, `a, b and c`.
fn join_and(items: &[String]) -> String {
    match items.split_last() {
        Some((last, rest)) if !rest.is_empty() => format!("{} and {last}", rest.join(", ")),
        _ => items.join(""),
    }
}

/// Past verb, running verb, and singular and plural nouns of a known kind.
pub(super) fn category(
    kind: &str,
) -> Option<(&'static str, &'static str, &'static str, &'static str)> {
    Some(match kind {
        "file_read" => ("read", "reading", "file", "files"),
        "file_edit" => ("edited", "editing", "file", "files"),
        "file_write" => ("wrote", "writing", "file", "files"),
        "file_search" => ("ran", "running", "search", "searches"),
        "shell" => ("ran", "running", "command", "commands"),
        "web_search" => ("ran", "running", "web search", "web searches"),
        "web_fetch" => ("fetched", "fetching", "page", "pages"),
        "todo" => ("updated todos", "updating todos", "time", "times"),
        "user_question" => ("asked", "asking", "question", "questions"),
        "skill" => ("loaded", "loading", "skill", "skills"),
        "subagent" => ("ran", "running", "subagent", "subagents"),
        "worktree" => ("created", "creating", "worktree", "worktrees"),
        _ => return None,
    })
}
