//! The composer's top-border title: the last answer's rate, then the agent and approval policy.

use ratatui::style::Color;
use ratatui::text::{Line, Span};
use unicode_width::UnicodeWidthStr;

use super::theme;
use crate::agents;
use crate::app::App;
use crate::server::AgentSafety;

/// Between the rate, the agent and the policy.
const SEP: &str = " · ";

/// The policy label's color per safety; the borders stay neutral.
fn safety_color(safety: AgentSafety) -> Color {
    match safety {
        AgentSafety::Safe => theme::success(),
        AgentSafety::Neutral => theme::muted(),
        AgentSafety::Destructive | AgentSafety::Smart => theme::warning(),
        AgentSafety::Yolo => theme::error(),
    }
}

/// The last turn's output tokens per second, e.g. `42 tok/s`; empty until a turn measured one.
pub fn rate(tokens_per_second: f64) -> String {
    match tokens_per_second {
        tps if tps <= 0.0 => String::new(),
        tps if tps < 10.0 => format!("{tps:.1} tok/s"),
        tps => format!("{tps:.0} tok/s"),
    }
}

/// ` 42 tok/s · lean · auto approve ─`, dropping the rate first when the line is too narrow.
pub fn title(app: &App, width: u16) -> Line<'static> {
    let policy = agents::displayed(app);
    let bypass = agents::bypass_tool_permissions(app);
    let policy_name = agents::indicator_policy_name(policy, bypass);
    let mode = match agents::indicator_agent_name(app) {
        Some(agent) => format!("{agent}{SEP}{policy_name}"),
        None => policy_name,
    };
    let mode_style = theme::text(safety_color(agents::indicator_safety(policy, bypass)));
    let rate = rate(app.session.stats.tokens_per_second);
    // The border keeps a corner of its own on each side of the title.
    let room = (width as usize).saturating_sub(2);
    let rate = match rate.width() + SEP.width() + mode.width() <= room {
        true => rate,
        false => String::new(),
    };
    let mut spans = vec![Span::raw(" ")];
    if !rate.is_empty() {
        spans.push(Span::styled(rate, theme::muted_style()));
        spans.push(Span::styled(SEP, theme::muted_style()));
    }
    if !mode.is_empty() {
        spans.push(Span::styled(format!("{mode} "), mode_style));
    }
    spans.push(Span::styled("─", theme::border_style()));
    Line::from(spans)
}

/// The bottom-border hint shown while Ctrl+S holds a stashed draft and can restore it.
pub fn stash_hint(app: &App) -> Line<'static> {
    if app.chat_input.stash.is_none() || !crate::composer_stash::key_reaches_stash(app) {
        return Line::default();
    }
    let hint = (
        crate::hints::key::CTRL_S,
        crate::hints::action::RESTORE_STASH,
    );
    let mut spans = vec![Span::raw(" ")];
    spans.extend(super::hint_line::spans(&[hint]));
    spans.push(Span::raw(" "));
    spans.push(Span::styled("─", theme::border_style()));
    Line::from(spans).right_aligned()
}
