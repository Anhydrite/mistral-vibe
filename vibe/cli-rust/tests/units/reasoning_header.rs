//! A live reasoning trace counts the lines it has streamed so far.

use serde_json::json;
use vibe_rs::app::App;

use crate::support::{render, rows};

fn screen(text: &str, status: &str) -> String {
    let mut app = App::default();
    app.view.transcript.set_show_reasoning(true);
    app.view.transcript.add(&json!({
        "entry": {
            "id": "r1",
            "type": "reasoning",
            "text": text,
            "generationStatus": status,
        }
    }));
    let buffer = render(80, 12, |frame| {
        vibe_rs::ui::transcript::draw(&mut app, frame, frame.area());
    });
    rows(&buffer).join("\n")
}

#[test]
fn a_live_trace_shows_its_line_count() {
    let screen = screen("first line\nsecond line\nthird line", "in_progress");
    assert!(screen.contains("Thinking · 3 lines"), "{screen}");
}

#[test]
fn a_single_streamed_line_is_not_plural() {
    let screen = screen("only one", "in_progress");
    assert!(screen.contains("Thinking · 1 line"), "{screen}");
}

#[test]
fn a_settled_trace_drops_the_count() {
    let screen = screen("first line\nsecond line", "completed");
    assert!(screen.contains("Thought"), "{screen}");
    assert!(!screen.contains("lines"), "{screen}");
}
