# Native GUI Frameworks

Comprehensive guide to pure Rust GUI frameworks: egui, iced, slint, and druid. When you need maximum performance, no web dependencies, or specialized UI patterns.

## Framework Overview

### Comparison Matrix

| Framework | Paradigm | Rendering | Best For | Maturity | Bundle Size |
|-----------|----------|-----------|----------|----------|-------------|
| **egui** | Immediate Mode | CPU (optional GPU) | Tools, editors, games | Mature | ~3MB |
| **iced** | Elm Architecture | GPU (wgpu) | Cross-platform apps | Growing | ~5MB |
| **slint** | Declarative | GPU/CPU | Embedded, desktop | Mature | ~4MB |
| **druid** | Data-first | GPU (piet) | Reactive apps | Maintenance | ~4MB |

### When to Use Each

**egui (Immediate Mode)**
- ✅ Game editors, debug tools, developer tools
- ✅ Rapid prototyping, quick iterations
- ✅ Dynamic UIs that change frequently
- ✅ Integration with game engines (Bevy, macroquad)
- ❌ Complex state management
- ❌ Strict design systems

**iced (Elm Architecture)**
- ✅ Cross-platform consistency
- ✅ Type-safe state management
- ✅ Predictable updates
- ✅ Custom widgets
- ❌ Steep learning curve
- ❌ Limited ecosystem

**slint (Declarative UI)**
- ✅ Embedded systems, IoT devices
- ✅ Designer-developer collaboration
- ✅ Declarative markup language
- ✅ Touch-first interfaces
- ❌ Larger binary size
- ❌ Proprietary markup

**druid (Data-first)**
- ✅ Data-driven applications
- ✅ Lens-based state management
- ✅ Widget composition
- ❌ Maintenance mode (archived)
- ❌ Limited documentation

## egui - Immediate Mode GUI

### Architecture

Immediate mode means UI is rebuilt every frame based on current state. No separate UI tree or state synchronization.

**Core Concepts:**
```rust
// Every frame:
1. Read input events
2. Run application logic
3. Build UI from scratch
4. Render output
```

### Setup

```toml
# Cargo.toml
[dependencies]
eframe = "0.27"  # egui + native windowing
egui = "0.27"

# Optional: Additional widgets
egui_extras = "0.27"
egui_plot = "0.27"
```

### Basic Application

```rust
use eframe::egui;

fn main() -> Result<(), eframe::Error> {
    let options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_inner_size([800.0, 600.0]),
        ..Default::default()
    };

    eframe::run_native(
        "My egui App",
        options,
        Box::new(|_cc| Box::new(MyApp::default())),
    )
}

struct MyApp {
    name: String,
    age: u32,
}

impl Default for MyApp {
    fn default() -> Self {
        Self {
            name: "Arthur".to_owned(),
            age: 42,
        }
    }
}

impl eframe::App for MyApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        egui::CentralPanel::default().show(ctx, |ui| {
            ui.heading("My egui Application");

            ui.horizontal(|ui| {
                ui.label("Name:");
                ui.text_edit_singleline(&mut self.name);
            });

            ui.add(egui::Slider::new(&mut self.age, 0..=120).text("age"));

            if ui.button("Click me!").clicked() {
                println!("Hello, {}! You are {} years old.", self.name, self.age);
            }
        });
    }
}
```

### Layout Patterns

```rust
impl eframe::App for MyApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        // Top panel
        egui::TopBottomPanel::top("top_panel").show(ctx, |ui| {
            egui::menu::bar(ui, |ui| {
                ui.menu_button("File", |ui| {
                    if ui.button("Open").clicked() {
                        // Handle open
                    }
                    if ui.button("Save").clicked() {
                        // Handle save
                    }
                });
            });
        });

        // Side panel
        egui::SidePanel::left("side_panel").show(ctx, |ui| {
            ui.heading("Settings");
            ui.separator();
            // Settings content
        });

        // Bottom panel
        egui::TopBottomPanel::bottom("bottom_panel").show(ctx, |ui| {
            ui.horizontal(|ui| {
                ui.label("Status: Ready");
            });
        });

        // Central panel (fills remaining space)
        egui::CentralPanel::default().show(ctx, |ui| {
            ui.heading("Main Content");
            // Main application content
        });
    }
}
```

### Widgets

```rust
// Text input
ui.text_edit_singleline(&mut self.text);
ui.text_edit_multiline(&mut self.multiline_text);

// Buttons
if ui.button("Click me").clicked() { }
if ui.small_button("Small").clicked() { }
ui.add_enabled(false, egui::Button::new("Disabled"));

// Checkboxes and radio
ui.checkbox(&mut self.checked, "Check me");
ui.radio_value(&mut self.choice, Choice::A, "Option A");
ui.radio_value(&mut self.choice, Choice::B, "Option B");

// Sliders and drag values
ui.add(egui::Slider::new(&mut self.value, 0.0..=100.0));
ui.add(egui::DragValue::new(&mut self.value).speed(0.1));

// Combo box (dropdown)
egui::ComboBox::from_label("Select item")
    .selected_text(format!("{:?}", self.selected))
    .show_ui(ui, |ui| {
        ui.selectable_value(&mut self.selected, Item::A, "Item A");
        ui.selectable_value(&mut self.selected, Item::B, "Item B");
    });

// Color picker
ui.color_edit_button_rgb(&mut self.color);

// Images
ui.image(egui::include_image!("icon.png"));

// Plotting
use egui_plot::{Line, Plot, PlotPoints};
let sin: PlotPoints = (0..1000)
    .map(|i| {
        let x = i as f64 * 0.01;
        [x, x.sin()]
    })
    .collect();
Plot::new("my_plot").show(ui, |plot_ui| {
    plot_ui.line(Line::new(sin));
});
```

### Custom Widgets

```rust
fn custom_widget(ui: &mut egui::Ui, value: &mut f32) -> egui::Response {
    let desired_size = ui.spacing().interact_size.y * egui::vec2(2.0, 1.0);
    let (rect, response) = ui.allocate_exact_size(desired_size, egui::Sense::click());

    if ui.is_rect_visible(rect) {
        let visuals = ui.style().interact(&response);
        let rect = rect.expand(visuals.expansion);
        let radius = 0.5 * rect.height();

        ui.painter()
            .rect(rect, radius, visuals.bg_fill, visuals.bg_stroke);

        // Draw custom content
        let text = format!("{:.1}", value);
        ui.painter().text(
            rect.center(),
            egui::Align2::CENTER_CENTER,
            text,
            egui::FontId::default(),
            visuals.text_color(),
        );
    }

    response
}
```

### State Management with egui

```rust
use std::sync::{Arc, Mutex};

struct SharedState {
    data: Arc<Mutex<AppData>>,
}

struct AppData {
    counter: i32,
    items: Vec<String>,
}

impl eframe::App for MyApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        let mut data = self.state.data.lock().unwrap();

        egui::CentralPanel::default().show(ctx, |ui| {
            ui.label(format!("Counter: {}", data.counter));

            if ui.button("Increment").clicked() {
                data.counter += 1;
            }

            for item in &data.items {
                ui.label(item);
            }
        });
    }
}
```

## iced - Elm Architecture

### Architecture

Iced follows The Elm Architecture: Model (state) + Update (state changes) + View (UI).

```
┌─────────────┐
│    View     │ ─── Displays state
└──────┬──────┘
       │ User interaction
       ▼
┌─────────────┐
│  Message    │ ─── Event/action
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Update    │ ─── Modifies state
└──────┬──────┘
       │
       ▼
┌─────────────┐
│    Model    │ ─── Application state
└─────────────┘
```

### Setup

```toml
[dependencies]
iced = "0.12"
```

### Basic Application

```rust
use iced::{
    widget::{button, column, text, text_input},
    Element, Sandbox, Settings,
};

pub fn main() -> iced::Result {
    Counter::run(Settings::default())
}

struct Counter {
    value: i32,
    input: String,
}

#[derive(Debug, Clone)]
enum Message {
    Increment,
    Decrement,
    Reset,
    InputChanged(String),
}

impl Sandbox for Counter {
    type Message = Message;

    fn new() -> Self {
        Self {
            value: 0,
            input: String::new(),
        }
    }

    fn title(&self) -> String {
        String::from("Counter - Iced")
    }

    fn update(&mut self, message: Message) {
        match message {
            Message::Increment => {
                self.value += 1;
            }
            Message::Decrement => {
                self.value -= 1;
            }
            Message::Reset => {
                self.value = 0;
            }
            Message::InputChanged(value) => {
                self.input = value;
            }
        }
    }

    fn view(&self) -> Element<Message> {
        column![
            button("Increment").on_press(Message::Increment),
            text(self.value).size(50),
            button("Decrement").on_press(Message::Decrement),
            button("Reset").on_press(Message::Reset),
            text_input("Type something...", &self.input)
                .on_input(Message::InputChanged),
        ]
        .padding(20)
        .into()
    }
}
```

### Advanced Application with Commands

```rust
use iced::{Application, Command, Element, Settings, Theme};
use iced::widget::{button, column, text};

pub fn main() -> iced::Result {
    MyApp::run(Settings::default())
}

struct MyApp {
    state: AppState,
    data: Option<String>,
}

enum AppState {
    Idle,
    Loading,
    Loaded,
    Error(String),
}

#[derive(Debug, Clone)]
enum Message {
    LoadData,
    DataLoaded(Result<String, String>),
}

impl Application for MyApp {
    type Executor = iced::executor::Default;
    type Message = Message;
    type Theme = Theme;
    type Flags = ();

    fn new(_flags: ()) -> (Self, Command<Message>) {
        (
            Self {
                state: AppState::Idle,
                data: None,
            },
            Command::none(),
        )
    }

    fn title(&self) -> String {
        String::from("Async App - Iced")
    }

    fn update(&mut self, message: Message) -> Command<Message> {
        match message {
            Message::LoadData => {
                self.state = AppState::Loading;
                Command::perform(fetch_data(), Message::DataLoaded)
            }
            Message::DataLoaded(Ok(data)) => {
                self.state = AppState::Loaded;
                self.data = Some(data);
                Command::none()
            }
            Message::DataLoaded(Err(error)) => {
                self.state = AppState::Error(error);
                Command::none()
            }
        }
    }

    fn view(&self) -> Element<Message> {
        let content = match &self.state {
            AppState::Idle => {
                column![button("Load Data").on_press(Message::LoadData)]
            }
            AppState::Loading => {
                column![text("Loading...")]
            }
            AppState::Loaded => {
                column![
                    text(self.data.as_ref().unwrap()),
                    button("Reload").on_press(Message::LoadData),
                ]
            }
            AppState::Error(error) => {
                column![
                    text(format!("Error: {}", error)),
                    button("Retry").on_press(Message::LoadData),
                ]
            }
        };

        content.padding(20).into()
    }

    fn theme(&self) -> Theme {
        Theme::Dark
    }
}

async fn fetch_data() -> Result<String, String> {
    tokio::time::sleep(tokio::time::Duration::from_secs(2)).await;
    Ok("Data loaded successfully!".to_string())
}
```

### Custom Widgets in iced

```rust
use iced::widget::canvas::{self, Cache, Canvas, Cursor, Frame, Geometry, Path};
use iced::{Color, Element, Length, Point, Rectangle, Size, Theme};

struct CircleWidget {
    cache: Cache,
}

impl CircleWidget {
    fn new() -> Self {
        Self {
            cache: Cache::default(),
        }
    }
}

impl<Message> canvas::Program<Message> for CircleWidget {
    type State = ();

    fn draw(
        &self,
        _state: &(),
        renderer: &iced::Renderer,
        _theme: &Theme,
        bounds: Rectangle,
        _cursor: Cursor,
    ) -> Vec<Geometry> {
        let geometry = self.cache.draw(renderer, bounds.size(), |frame| {
            let center = frame.center();
            let radius = frame.width().min(frame.height()) / 4.0;

            let circle = Path::circle(center, radius);
            frame.fill(&circle, Color::from_rgb(0.0, 0.5, 1.0));
        });

        vec![geometry]
    }
}

// Usage in view
fn view(&self) -> Element<Message> {
    Canvas::new(CircleWidget::new())
        .width(Length::Fill)
        .height(Length::Fill)
        .into()
}
```

### Styling in iced

```rust
use iced::widget::button::{self, Button};
use iced::widget::container::{self, Container};
use iced::{Background, Border, Color, Theme};

struct CustomButtonStyle;

impl button::StyleSheet for CustomButtonStyle {
    type Style = Theme;

    fn active(&self, _style: &Self::Style) -> button::Appearance {
        button::Appearance {
            background: Some(Background::Color(Color::from_rgb(0.2, 0.6, 1.0))),
            text_color: Color::WHITE,
            border: Border {
                radius: 5.0.into(),
                ..Default::default()
            },
            ..Default::default()
        }
    }

    fn hovered(&self, style: &Self::Style) -> button::Appearance {
        let active = self.active(style);

        button::Appearance {
            background: Some(Background::Color(Color::from_rgb(0.3, 0.7, 1.0))),
            ..active
        }
    }
}

// Usage
button("Custom Styled Button").style(CustomButtonStyle)
```

## slint - Declarative UI

### Architecture

Slint uses a declarative markup language (.slint files) compiled to Rust code.

### Setup

```toml
[dependencies]
slint = "1.5"

[build-dependencies]
slint-build = "1.5"
```

**build.rs:**
```rust
fn main() {
    slint_build::compile("ui/app.slint").unwrap();
}
```

### Basic Application

**ui/app.slint:**
```slint
import { Button, VerticalBox, HorizontalBox, LineEdit } from "std-widgets.slint";

export component App inherits Window {
    in-out property<int> counter: 0;
    in-out property<string> name: "World";

    VerticalBox {
        Text {
            text: "Counter: \{counter}";
            font-size: 24px;
        }

        HorizontalBox {
            Button {
                text: "Increment";
                clicked => {
                    counter += 1;
                }
            }

            Button {
                text: "Decrement";
                clicked => {
                    counter -= 1;
                }
            }
        }

        LineEdit {
            placeholder-text: "Enter name";
            text <=> name;
        }

        Text {
            text: "Hello, \{name}!";
        }
    }
}
```

**main.rs:**
```rust
slint::include_modules!();

fn main() {
    let app = App::new().unwrap();

    // Access properties
    app.set_counter(10);
    println!("Counter: {}", app.get_counter());

    // Run application
    app.run().unwrap();
}
```

### Advanced slint Features

**Callbacks:**
```slint
export component App inherits Window {
    callback button-clicked(string);

    Button {
        text: "Click me";
        clicked => {
            button-clicked("Button was clicked!");
        }
    }
}
```

```rust
slint::include_modules!();

fn main() {
    let app = App::new().unwrap();

    app.on_button_clicked(|msg| {
        println!("Callback: {}", msg);
    });

    app.run().unwrap();
}
```

**Custom Structs:**
```slint
export struct Person {
    name: string,
    age: int,
}

export component App inherits Window {
    in-out property<Person> user: { name: "Alice", age: 30 };

    Text {
        text: "\{user.name} is \{user.age} years old";
    }
}
```

```rust
use slint::Model;

slint::include_modules!();

fn main() {
    let app = App::new().unwrap();

    let person = Person {
        name: "Bob".into(),
        age: 25,
    };
    app.set_user(person);

    app.run().unwrap();
}
```

**Lists and Models:**
```slint
export component App inherits Window {
    in-out property<[string]> items: ["Item 1", "Item 2", "Item 3"];

    VerticalBox {
        for item in items: Text {
            text: item;
        }
    }
}
```

```rust
use slint::{Model, ModelRc, VecModel};

slint::include_modules!();

fn main() {
    let app = App::new().unwrap();

    let model = Rc::new(VecModel::from(vec![
        "Dynamic Item 1".into(),
        "Dynamic Item 2".into(),
    ]));

    app.set_items(ModelRc::from(model.clone()));

    app.run().unwrap();
}
```

## druid (Archived - Reference Only)

Druid is in maintenance mode but offers valuable patterns for data-driven UIs.

### Core Concepts

**Lens Pattern:**
```rust
use druid::widget::{Button, Flex, Label, TextBox};
use druid::{AppLauncher, Data, Lens, Widget, WindowDesc};

#[derive(Clone, Data, Lens)]
struct AppState {
    name: String,
    count: u32,
}

fn build_ui() -> impl Widget<AppState> {
    Flex::column()
        .with_child(Label::new(|data: &AppState, _env: &_| {
            format!("Hello, {}!", data.name)
        }))
        .with_child(TextBox::new().lens(AppState::name))
        .with_child(Label::new(|data: &AppState, _env: &_| {
            format!("Count: {}", data.count)
        }))
        .with_child(Button::new("Increment").on_click(|_ctx, data: &mut AppState, _env| {
            data.count += 1;
        }))
}

fn main() {
    let main_window = WindowDesc::new(build_ui())
        .title("Druid App")
        .window_size((400.0, 300.0));

    let initial_state = AppState {
        name: "World".to_string(),
        count: 0,
    };

    AppLauncher::with_window(main_window)
        .launch(initial_state)
        .expect("Failed to launch application");
}
```

## Framework Selection Guide

### Decision Tree

```
Choose GUI framework based on:

Project Type:
├─ Game editor, debug tools → egui
├─ Cross-platform app with complex state → iced
├─ Embedded device, touch interface → slint
└─ Data-driven (consider alternatives) → druid/iced

Development Speed:
├─ Rapid prototyping → egui
├─ Type-safe architecture → iced
└─ Designer collaboration → slint

Performance Needs:
├─ 60+ FPS immediate updates → egui
├─ GPU-accelerated rendering → iced/slint
└─ Minimal CPU usage → slint

Team Experience:
├─ Immediate mode GUI → egui
├─ Elm/functional programming → iced
└─ QML/declarative UI → slint
```

### Migration Paths

**From web to native:**
- Tauri → egui: Extract backend, rebuild UI
- React → iced: Messages ≈ Actions, State ≈ Model

**Between native frameworks:**
- egui → iced: Refactor to Elm architecture
- iced → slint: Extract logic, rebuild in .slint

## Production Tips

### Performance

**egui:**
- Use `ui.ctx().request_repaint()` sparingly
- Cache expensive computations
- Profile with `puffin` profiler

**iced:**
- Minimize `Command` usage
- Use `subscription` for continuous updates
- Batch state updates

**slint:**
- Use `property` bindings efficiently
- Optimize model updates
- Profile with built-in tools

### Distribution

All frameworks support:
- Static binaries (3-10MB)
- Cross-compilation
- Native installers (MSI, DMG, DEB)

### Testing

**egui:**
```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_app_logic() {
        let mut app = MyApp::default();
        // Test state changes
        assert_eq!(app.counter, 0);
    }
}
```

**iced:**
```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_update() {
        let mut app = Counter::new();
        app.update(Message::Increment);
        assert_eq!(app.value, 1);
    }
}
```

This guide covers production-ready patterns for all major Rust GUI frameworks. Choose based on project needs, team skills, and performance requirements.
