import os
import json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QComboBox,
    QTextEdit, QScrollArea
)
from PyQt6.QtCore import Qt

import config

AGENT_PROMPT_PAIRS = [
    ("floor_plan_parser.json", "v1_parse_floor_plan.md"),
    ("egress_validator.json", "v1_check_egress.md"),
    ("evacuation_diagnoser.json", "v1_diagnose_issues.md"),
    ("exit_placement_advisor.json", "v1_propose_fixes.md"),
]

_PAIR_ANNOTATIONS = [
    [
        "Structured I/O: Legacy pastes raw image data into a prompt. Agent defines a typed 'image' input and produces a JSON floor plan schema as output.",
        "Tool access: Agent uses Gemini Vision API as a registered tool — the prompt has no tool concept.",
        "Conversation: Agent proactively flags ambiguous features (unusual room shapes) and asks for clarification. Legacy gives a one-shot answer.",
        "Reusability: Anyone can run the Floor Plan Parser agent without knowing how the prompt works.",
    ],
    [
        "Structured I/O: Legacy expects pasted JSON in a text prompt. Agent declares a typed 'json' input field and outputs a structured violation list.",
        "Tool access: Agent calls P118 Validator and Pathfinding tools for real calculations. Legacy relies on the LLM to guess distances and rules.",
        "Constraints: Agent explicitly lists P118 rules (30m travel, 1.4m corridors, min 2 exits). Legacy buries them in prose instructions.",
        "Reusability: The Egress Validator agent can be re-run on any floor plan without modifying the prompt.",
    ],
    [
        "Structured I/O: Legacy returns free-form text explanation. Agent produces ranked diagnoses with severity and impact scores.",
        "Conversation: Agent can answer follow-up questions about specific violations. Legacy requires re-sending the entire prompt.",
        "Scope boundaries: Agent redirects validation questions to the Egress Validator agent instead of guessing.",
        "Constraints: Agent uses severity ranking rules to prioritize which violations to explain first.",
    ],
    [
        "Structured I/O: Legacy gives text suggestions. Agent produces ranked fix proposals with justification and effort estimates.",
        "Tool access: Agent calls Pathfinding and P118 Validator to verify that proposed fixes actually resolve violations. Legacy cannot verify.",
        "Conversation: Agent handles pushback ('Can't add a south exit') and offers alternatives. Legacy is one-shot.",
        "Constraints: Agent respects building constraints and checks proposals against P118 rules before suggesting them.",
    ],
]


class AdoptionPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AdoptionPanel")
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        main_layout.addWidget(scroll_area)

        wrapper = QWidget()
        scroll_area.setWidget(wrapper)
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(16, 16, 16, 16)
        wrapper_layout.setSpacing(12)

        # ── Title ───────────────────────────────────────────────
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        title_row.setContentsMargins(0, 0, 0, 0)

        _here = os.path.dirname(os.path.abspath(__file__))
        _icon_path = os.path.join(_here, "assets", "icons", "increase.png")
        if os.path.isfile(_icon_path):
            from PyQt6.QtGui import QPixmap
            from PyQt6.QtCore import Qt as _Qt
            icon_lbl = QLabel()
            icon_lbl.setPixmap(QPixmap(_icon_path).scaled(24, 24, _Qt.AspectRatioMode.KeepAspectRatio,
                                                          _Qt.TransformationMode.SmoothTransformation))
            title_row.addWidget(icon_lbl)

        title_lbl = QLabel("Legacy vs Agent — Side-by-Side Comparison")
        title_lbl.setProperty("class", "Title")
        title_row.addWidget(title_lbl)
        title_row.addStretch()
        wrapper_layout.addLayout(title_row)

        # ── Summary banner ──────────────────────────────────────
        banner = QFrame()
        banner.setProperty("class", "Card")
        banner_layout = QVBoxLayout(banner)

        summary_lbl = QLabel(
            "Same task. Legacy = copy-paste + raw text. Agent = structured agents with tools and conversation."
        )
        summary_lbl.setWordWrap(True)
        banner_layout.addWidget(summary_lbl)
        wrapper_layout.addWidget(banner)

        # ── Pair selector ───────────────────────────────────────
        selector = QFrame()
        selector_layout = QHBoxLayout(selector)
        selector_layout.setContentsMargins(0, 0, 0, 0)

        selector_layout.addWidget(QLabel("Select pair:"))

        self.pair_combo = QComboBox()
        pair_names = [p[0].replace(".json", "").replace("_", " ").title() for p in AGENT_PROMPT_PAIRS]
        self.pair_combo.addItems(pair_names)
        self.pair_combo.currentTextChanged.connect(self._on_pair_selected)
        selector_layout.addWidget(self.pair_combo)
        selector_layout.addStretch()

        wrapper_layout.addWidget(selector)

        # ── Two-column comparison ───────────────────────────────
        columns = QFrame()
        columns_layout = QHBoxLayout(columns)
        columns_layout.setContentsMargins(0, 0, 0, 0)

        # Legacy side
        left_card = QFrame()
        left_card.setProperty("class", "Card")
        left_layout = QVBoxLayout(left_card)
        left_title = QLabel("Legacy — Prompt Template")
        left_title.setProperty("class", "Subtitle")
        left_layout.addWidget(left_title)

        self.l2_text = QTextEdit()
        self.l2_text.setReadOnly(True)
        self.l2_text.setMinimumHeight(200)
        left_layout.addWidget(self.l2_text)
        columns_layout.addWidget(left_card, 5)

        # Arrow column
        arrow_frame = QFrame()
        arrow_layout = QVBoxLayout(arrow_frame)
        arrow_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        arrow_layout.addWidget(QLabel("→"))
        arrow_layout.addWidget(QLabel("Legacy→Agent"))
        arrow_layout.addWidget(QLabel("→"))
        columns_layout.addWidget(arrow_frame, 1)

        # Agent side
        right_card = QFrame()
        right_card.setProperty("class", "Card")
        right_layout = QVBoxLayout(right_card)
        right_title = QLabel("Agent — Agent Definition")
        right_title.setProperty("class", "Subtitle")
        right_layout.addWidget(right_title)

        self.l3_text = QTextEdit()
        self.l3_text.setReadOnly(True)
        self.l3_text.setMinimumHeight(200)
        right_layout.addWidget(self.l3_text)
        columns_layout.addWidget(right_card, 5)

        wrapper_layout.addWidget(columns, 1)

        # ── Annotations ─────────────────────────────────────────
        self.ann_card = QFrame()
        self.ann_card.setProperty("class", "Card")
        self.ann_layout = QVBoxLayout(self.ann_card)

        ann_title = QLabel("What Changed: Legacy → Agent")
        ann_title.setProperty("class", "Title")
        self.ann_layout.addWidget(ann_title)

        self.ann_container = QFrame()
        self.ann_container_layout = QVBoxLayout(self.ann_container)
        self.ann_container_layout.setContentsMargins(0, 0, 0, 0)
        self.ann_layout.addWidget(self.ann_container)

        wrapper_layout.addWidget(self.ann_card)

        # Load initial pair
        if pair_names:
            self._on_pair_selected(pair_names[0])

    def _on_pair_selected(self, selected_value):
        pair_names = [p[0].replace(".json", "").replace("_", " ").title() for p in AGENT_PROMPT_PAIRS]
        if selected_value not in pair_names:
            return
        idx = pair_names.index(selected_value)

        agent_file, prompt_file = AGENT_PROMPT_PAIRS[idx]

        prompt_path = os.path.join(config.PROMPTS_DIR, prompt_file)
        agent_path = os.path.join(config.AGENTS_DIR, agent_file)

        # Legacy side
        if os.path.isfile(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.l2_text.setPlainText(f.read())
        else:
            self.l2_text.setPlainText("(Template not found)")

        # Agent side
        if os.path.isfile(agent_path):
            with open(agent_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.l3_text.setPlainText(json.dumps(data, indent=2))
        else:
            self.l3_text.setPlainText("(Agent definition not found)")

        # Update annotations for this pair
        while self.ann_container_layout.count():
            child = self.ann_container_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        annotations = _PAIR_ANNOTATIONS[idx] if idx < len(_PAIR_ANNOTATIONS) else []
        for a in annotations:
            lbl = QLabel(f"• {a}")
            lbl.setWordWrap(True)
            self.ann_container_layout.addWidget(lbl)