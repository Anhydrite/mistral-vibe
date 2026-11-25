//! The bottom bar names the active model; a plain click on it opens `/model`, busy turns, drags and double clicks do not.

use crossterm::event::{MouseButton, MouseEventKind};
use ratatui::buffer::Buffer;
use tokio::sync::mpsc;

use vibe_rs::app::{App, Status};
use vibe_rs::pointer::{self, Shape};
use vibe_rs::telemetry::{self, event, TelemetryEvent};
use vibe_rs::ui::{bottom_bar, theme};

use crate::support::{click, column, mouse, redraw, row, send_mouse};

const MODEL: &str = "mistral-medium-3.5[medium]";

/// A ready session painted at 80x24, and the model's cell in the bottom bar.
fn bar() -> (App, (u16, u16)) {
    let mut app = App::default();
    app.set_status(Status::Ready);
    app.session.cwd = Some("/tmp/project".into());
    app.session.tokens = (0, 600_000);
    app.session.startup_config.active_model = MODEL.into();
    let at = model_cell(&redraw(&mut app));
    (app, at)
}

/// The bar's row, and the model's first column on it.
fn model_cell(buffer: &Buffer) -> (u16, u16) {
    let y = buffer.area.height - 1;
    let text = row(buffer, y);
    (column(&text, "mistral-medium"), y)
}

/// Hovering the model shows no link style or hand, and a click leaves `/model` closed.
fn assert_inert(app: &mut App, (x, y): (u16, u16)) {
    let plain = redraw(app)[(x + 2, y)].style();
    hover(app, (x + 2, y));
    let buffer = redraw(app);
    assert!(!bottom_bar::model_at(app, (x + 2, y)));
    assert_ne!(pointer::shape(app), Shape::Pointer);
    assert_eq!(buffer[(x + 2, y)].style(), plain);

    click(app, x + 2, y);
    assert!(!app.model_picker.open);
}

fn send(app: &mut App, kind: MouseEventKind, (x, y): (u16, u16)) {
    send_mouse(app, mouse(kind, x, y));
}

fn hover(app: &mut App, at: (u16, u16)) {
    send(app, MouseEventKind::Moved, at);
}

#[test]
fn the_bar_names_the_model_before_the_gauges() {
    let (mut app, (x, y)) = bar();
    let buffer = redraw(&mut app);
    let text = row(&buffer, y);
    let at = |name: &str| buffer[(column(&text, name), y)].style();

    assert!(
        text.contains(" mistral-medium-3.5[medium] · ctx"),
        "{text:?}"
    );
    assert_eq!(at("mistral").fg, Some(theme::foreground()));
    assert_eq!(x, column(&text, "mistral-medium"));
}

#[test]
fn a_plain_click_on_the_model_opens_the_picker_and_records_the_bar_entry() {
    let (mut app, (x, y)) = bar();
    let (tx, mut rx) = mpsc::channel(telemetry::TELEMETRY_CHANNEL_CAP);
    app.telemetry_tx = Some(tx);

    click(&mut app, x + 2, y);

    assert!(app.model_picker.open);
    let events: Vec<TelemetryEvent> = std::iter::from_fn(|| rx.try_recv().ok()).collect();
    let names: Vec<_> = events.iter().map(|event| event.name).collect();
    assert_eq!(
        names,
        [event::MODEL_SELECTION_OPENED, event::SLASH_COMMAND_USED]
    );
    assert_eq!(events[0].properties["picker"], "model");
    assert_eq!(events[1].properties["command"], "model");
}

#[test]
fn a_click_on_the_gauges_or_the_cwd_does_not_open_the_picker() {
    let (mut app, _) = bar();
    let buffer = redraw(&mut app);
    let y = buffer.area.height - 1;
    let text = row(&buffer, y);
    click(&mut app, column(&text, "ctx"), y);
    click(&mut app, column(&text, "project"), y);

    assert!(!app.model_picker.open);
}

#[test]
fn the_model_is_neither_clickable_nor_hovered_while_a_turn_runs() {
    let (mut app, at) = bar();
    app.set_status(Status::Generating {
        since: vibe_rs::clock::now(),
    });

    assert_inert(&mut app, at);
}

#[test]
fn the_model_is_neither_clickable_nor_hovered_while_the_session_starts() {
    let (mut app, at) = bar();
    app.set_status(Status::Starting);

    assert_inert(&mut app, at);
}

#[test]
fn the_model_is_neither_clickable_nor_hovered_while_a_shell_command_runs() {
    let (mut app, at) = bar();
    app.session.shell_operation_id = Some("shell-1".into());

    assert_inert(&mut app, at);
}

#[test]
fn the_model_shows_the_link_style_and_pointer_hand_once_ready() {
    let (mut app, (x, y)) = bar();
    let plain = redraw(&mut app)[(x + 2, y)].style();

    hover(&mut app, (x + 2, y));
    let buffer = redraw(&mut app);

    assert_eq!(pointer::shape(&app), Shape::Pointer);
    assert_ne!(buffer[(x + 2, y)].style(), plain);
}

#[test]
fn a_drag_back_to_its_start_cell_does_not_open_the_picker() {
    let (mut app, (x, y)) = bar();

    send(
        &mut app,
        MouseEventKind::Down(MouseButton::Left),
        (x + 2, y),
    );
    send(
        &mut app,
        MouseEventKind::Drag(MouseButton::Left),
        (x + 6, y),
    );
    send(
        &mut app,
        MouseEventKind::Drag(MouseButton::Left),
        (x + 2, y),
    );
    send(&mut app, MouseEventKind::Up(MouseButton::Left), (x + 2, y));

    assert!(!app.model_picker.open);
}

#[test]
fn a_release_off_the_model_does_not_open_the_picker() {
    let (mut app, (x, y)) = bar();

    send(
        &mut app,
        MouseEventKind::Down(MouseButton::Left),
        (x + 2, y),
    );
    send(&mut app, MouseEventKind::Up(MouseButton::Left), (2, y));

    assert!(!app.model_picker.open);
}

#[test]
fn a_double_click_on_the_model_opens_the_picker() {
    let (mut app, (x, y)) = bar();

    click(&mut app, x + 2, y);
    redraw(&mut app);
    click(&mut app, x + 2, y);

    assert!(app.model_picker.open);
}
