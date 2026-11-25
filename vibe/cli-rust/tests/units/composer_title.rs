//! The composer's top border: the last turn's rate, then the agent and approval policy.

use vibe_rs::app::App;
use vibe_rs::ui::composer_title;

#[test]
fn the_rate_reads_tokens_per_second() {
    assert_eq!(composer_title::rate(0.0), "");
    assert_eq!(composer_title::rate(-1.0), "");
    assert_eq!(composer_title::rate(9.84), "9.8 tok/s");
    assert_eq!(composer_title::rate(41.6), "42 tok/s");
}

#[test]
fn the_border_leads_with_the_rate_then_the_mode() {
    let mut app = App::default();
    app.session.stats.tokens_per_second = 42.4;
    app.agents.active_policy.display_name = "Auto Approve".into();

    assert_eq!(
        composer_title::title(&app, 80).to_string(),
        " 42 tok/s · auto approve ─"
    );
}

#[test]
fn a_border_without_a_measured_rate_names_the_mode_alone() {
    let mut app = App::default();
    app.agents.active_policy.display_name = "Auto Approve".into();

    assert_eq!(
        composer_title::title(&app, 80).to_string(),
        " auto approve ─"
    );
}

#[test]
fn a_narrow_border_drops_the_rate_but_keeps_the_mode() {
    let mut app = App::default();
    app.session.stats.tokens_per_second = 42.4;
    app.agents.active_policy.display_name = "Accept Edits".into();

    assert_eq!(
        composer_title::title(&app, 34).to_string(),
        " 42 tok/s · accept edits ─"
    );
    assert_eq!(
        composer_title::title(&app, 20).to_string(),
        " accept edits ─"
    );
}
