import sys
import os
import base64
import io
import re
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QTextEdit,
    QHBoxLayout, QVBoxLayout, QSplitter, QScrollArea, QFrame,
    QFileDialog, QStackedWidget,
)
from PyQt5.QtGui import QPixmap, QFontDatabase, QFont, QTextDocument, QPainter

from PyQt5.QtCore import Qt
from PyQt5.QtPrintSupport import QPrinter
from openai import OpenAI
from pdfminer.high_level import extract_text
from dotenv import load_dotenv
import fitz  # PyMuPDF
import PIL.Image  # Pillow

class AnnotatedDocumentWindow(QWidget):
    def __init__(self, stacked_widget):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.trigger_phrases = []

        self.setStyleSheet("background-color: white;")
        main_layout = QVBoxLayout()

        # Top button layout
        back_button = QPushButton("Go Back to Main Page")
        back_button.setStyleSheet("""
            QPushButton {
                background-color: #dddddd;
                border-radius: 6px;
                padding: 8px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #cccccc;
            }
        """)
        back_button.setFont(QFont("Arial", 12, QFont.Bold))
        back_button.clicked.connect(self.go_back)

        generate_button = QPushButton("Generate")
        generate_button.setStyleSheet("""
            QPushButton {
                background-color: #dddddd;
                border-radius: 6px;
                padding: 8px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #cccccc;
            }
        """)
        generate_button.setFont(QFont("Arial", 12, QFont.Bold))
        generate_button.clicked.connect(self.generate_annotated_document)

        export_button = QPushButton("Export to PDF")
        export_button.setStyleSheet("""
            QPushButton {
                background-color: #dddddd;
                border-radius: 6px;
                padding: 8px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #cccccc;
            }
        """)
        export_button.setFont(QFont("Arial", 12, QFont.Bold))
        export_button.clicked.connect(self.export_to_pdf)

        button_layout = QHBoxLayout()
        button_layout.addWidget(back_button)
        button_layout.addWidget(generate_button)
        button_layout.addStretch()
        button_layout.addWidget(export_button)

        # Main content layout
        content_layout = QHBoxLayout()

        self.text_box = QTextEdit()
        self.text_box.setReadOnly(True)
        self.text_box.setStyleSheet("font-size: 14px; background-color: white; color: black; padding: 12px;")
        content_layout.addWidget(self.text_box)

        # Sidebar with colored buttons
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(300)
        self.sidebar.setStyleSheet("background-color: #f2f2f2; border-left: 1px solid #ccc;")

        sidebar_layout = QVBoxLayout()
        sidebar_layout.setContentsMargins(10, 10, 10, 10)
        sidebar_layout.setSpacing(12)

        bias_buttons = {
            "Narrative Bias": ("#1E90FF", "#E6F2FF"),
            "Sentiment Bias": ("#FF4500", "#FFE5DC"),
            "Regional Bias": ("#228B22", "#E5F4E5"),
            "Slant": ("#DAA520", "#FFF8DC"),
            "Coverage Depth": ("#FF8C00", "#FFEFD5")
        }

        for label, (text_color, bg_color) in bias_buttons.items():
            btn = QPushButton(label)
            btn.setFont(QFont("Arial", 12, QFont.Bold))
            btn.setStyleSheet(f"""
                QPushButton {{
                    color: {text_color};
                    background-color: {bg_color};
                    border: 1px solid #ccc;
                    border-radius: 6px;
                    padding: 6px;
                }}
                QPushButton:hover {{
                    background-color: #ddd;
                }}
            """)
            btn.setCursor(Qt.PointingHandCursor)

        # calls functions once button is clicked
            if label == "Narrative Bias":
                btn.clicked.connect(self.highlight_narrative_bias)
            elif label == "Sentiment Bias":
                btn.clicked.connect(self.highlight_sentiment_bias)
            elif label == "Regional Bias":
                btn.clicked.connect(self.highlight_regional_bias)    
            elif label == "Slant":
                btn.clicked.connect(self.highlight_slant) 
            elif label == "Coverage Depth":
                btn.clicked.connect(self.highlight_coverage_depth) 
            else:
                btn.clicked.connect(lambda checked=False, name=label: print(f"{name} button clicked (placeholder)"))
            sidebar_layout.addWidget(btn)

        sidebar_layout.addStretch()
        self.sidebar.setLayout(sidebar_layout)
        content_layout.addWidget(self.sidebar)

        main_layout.addLayout(button_layout)
        main_layout.addLayout(content_layout)
        self.setLayout(main_layout)
        self.explanation_summary_box = QTextEdit()
        self.explanation_summary_box.setReadOnly(True)
        self.explanation_summary_box.setStyleSheet("background-color: white; color: black; font-size: 13px;")
        self.explanation_summary_box.setFixedHeight(150)  # adjust height as needed
        sidebar_layout.addWidget(self.explanation_summary_box)

    def go_back(self):
        self.stacked_widget.setCurrentIndex(0)

    def export_to_pdf(self):
        filepath, _ = QFileDialog.getSaveFileName(self, "Export Annotated PDF", "", "PDF Files (*.pdf)")
        if not filepath:
            return
        if not filepath.endswith(".pdf"):
            filepath += ".pdf"

        document = QTextDocument()
        document.setHtml(self.text_box.toHtml())

        printer = QPrinter()
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(filepath)

        document.print_(printer)

    def load_article(self, article_path):
        try:
            with open(article_path, "r") as f:
                self.article_text = f.read()
            with open("trigger_phrases.txt", "r") as file:
                self.trigger_text = file.read()
            self.text_box.setHtml("<i>Press 'Generate' to highlight trigger phrases within the document, or use the buttons on the right to highlight where the types of bias are found.</i>")
        except Exception as e:
            self.text_box.setText("Could not load article text.\n\n" + str(e))

    def generate_annotated_document(self):
        if not hasattr(self, 'article_text') or not hasattr(self, 'trigger_text'):
            self.text_box.setText("Article or trigger phrases not loaded.")
            return

        self.text_box.setText("Generating annotated document...")
        QApplication.processEvents()
        highlighted_html = run_annotated_highlighted_article(self.article_text, self.trigger_text)

        highlighted_html = re.sub(r"```(?:html)?\n?", "", highlighted_html)
        highlighted_html = highlighted_html.replace("```", "")

        self.text_box.setHtml(f"<div style='font-size:14px; color:black;'>{highlighted_html}</div>")

    def highlight_narrative_bias(self):
        if not hasattr(self, 'article_text'):
            self.text_box.setText("Article not loaded.")
            return

        self.text_box.setText("Highlighting narrative bias...")
        QApplication.processEvents()

        highlighted_html = self.run_narrative_bias_highlight(self.article_text)
        highlighted_html = re.sub(r"^```(?:html)?\s*", "", highlighted_html.strip())
        highlighted_html = re.sub(r"\s*```$", "", highlighted_html)

        parts = highlighted_html.strip().split("\n\n")
        if len(parts) > 1:
            article_html = "\n\n".join(parts[:-2])  
            explanation_html = "\n\n".join(parts[-2:])  
        else:
            article_html = highlighted_html
            explanation_html = ""

        try:
            with open("explanation.txt", "w", encoding="utf-8") as f:
                f.write(explanation_html)
        except Exception as e:
            print(f"Error writing explanation.txt: {e}")

        combined_html = (
            f"<div style='font-size:14px; color:black;'>{article_html}</div>"
            f"<div style='font-size:14px; color:white;'>{explanation_html}</div>"
        )
       
        self.text_box.setHtml(combined_html)
        self.summarize_explanations()

    def run_narrative_bias_highlight(self, article_text):
        client = OpenAI()
        prompt = (
            "You are given an article. Identify two specific phrases that represent narrative bias.\n"
            "Highlight them in the full text using this format:\n"
            "- Wrap each paragraph in <p> tags.\n"
            "- For each narrative bias phrase, wrap it with this HTML span:\n"
            "  <span style='color:#1E90FF; font-weight:bold;'>phrase</span>\n\n"
            "After the full article, add **two blank lines**.\n"
            "Then, provide an explanation for each highlighted phrase in the following format:\n\n"
            "Phrase: \n"
            "Explanation of why it's an example of narrative bias.\n\n"
            "Separate each explanation with a single blank line.\n"
            "Return ONLY valid HTML that includes the full article (with highlighted phrases in <span style='color:blue'>blue</span>) "
            "and the list of formatted explanations underneath.\n"
            "Do not include any extra text or markdown outside of the HTML.\n\n"
            "Article:\n" + article_text
        )

        chat = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="gpt-4o-mini",
            max_tokens=3000,
        )

        html = chat.choices[0].message.content

        return html

    def highlight_sentiment_bias(self):
        if not hasattr(self, 'article_text'):
            self.text_box.setText("Article not loaded.")
            return

        self.text_box.setText("Highlighting sentiment bias...")
        QApplication.processEvents()

        highlighted_html = self.run_sentiment_bias_highlight(self.article_text)
        highlighted_html = re.sub(r"^```(?:html)?\s*", "", highlighted_html.strip())
        highlighted_html = re.sub(r"\s*```$", "", highlighted_html)

        parts = highlighted_html.strip().split("\n\n")
        if len(parts) > 1:
                article_html = "\n\n".join(parts[:-2])  
                explanation_html = "\n\n".join(parts[-2:])  
        else:
                article_html = highlighted_html
                explanation_html = ""

        try:
                with open("explanation.txt", "w", encoding="utf-8") as f:
                    f.write(explanation_html)
        except Exception as e:
                print(f"Error writing explanation.txt: {e}")

        combined_html = (
                f"<div style='font-size:14px; color:black;'>{article_html}</div>"
                f"<div style='font-size:14px; color:white;'>{explanation_html}</div>"
            )
        
        self.text_box.setHtml(combined_html)
        self.summarize_explanations()

    def run_sentiment_bias_highlight(self, article_text):
        client = OpenAI()
        prompt = (
            "You are given an article. Identify two specific phrases that represent sentiment bias.\n"
            "Highlight them in the full text using this format:\n"
            "- Wrap each paragraph in <p> tags.\n"
            "- For each sentiment bias phrase, wrap it with this HTML span:\n"
            "  <span style='color:#FF4500; font-weight:bold;'>phrase</span>\n\n"
            "After the full article, add **two blank lines**.\n"
            "Then, provide an explanation for each highlighted phrase in the following format:\n\n"
            "Phrase: \n"
            "Explanation of why it's an example of sentiment bias.\n\n"
            "Separate each explanation with a single blank line.\n"
            "Return ONLY valid HTML that includes the full article (with highlighted phrases in <span style='color:red'>red</span>) "
            "and the list of formatted explanations underneath.\n"
            "Do not include any extra text or markdown outside of the HTML.\n\n"
            "Article:\n" + article_text
        )
        

        chat = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="gpt-4o-mini",
            max_tokens=3000,
        )

        html = chat.choices[0].message.content

        return html


    def run_regional_bias_highlight(self, article_text):
        client = OpenAI()
        prompt = (
            "You are given an article. Identify two specific phrases that represent regional bias.\n"
            "Highlight them in the full text using this format:\n"
            "- Wrap each paragraph in <p> tags.\n"
            "- For each regional bias phrase, wrap it with this HTML span:\n"
            "  <span style='color:#228B22; font-weight:bold;'>phrase</span>\n\n"
            "After the full article, add **two blank lines**.\n"
             "Then, provide an explanation for each highlighted phrase in the following format:\n\n"
            "Phrase: \n"
            "Explanation of why it's an example of regional bias.\n\n"
            "Separate each explanation with a single blank line.\n"
            "Return ONLY valid HTML that includes the full article (with highlighted phrases in <span style='color:green'>green</span>) "
            "and the list of formatted explanations underneath.\n"
            "Do not include any extra text or markdown outside of the HTML.\n\n"
            "Article:\n" + article_text
        )
        

        chat = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="gpt-4o-mini",
            max_tokens=3000,
        )

        html = chat.choices[0].message.content

        return html
    
    def highlight_regional_bias(self):
        if not hasattr(self, 'article_text'):
            self.text_box.setText("Article not loaded.")
            return

        self.text_box.setText("Highlighting regional bias...")
        QApplication.processEvents()

        highlighted_html = self.run_regional_bias_highlight(self.article_text)
        highlighted_html = re.sub(r"^```(?:html)?\s*", "", highlighted_html.strip())
        highlighted_html = re.sub(r"\s*```$", "", highlighted_html)

        parts = highlighted_html.strip().split("\n\n")
        if len(parts) > 1:
            article_html = "\n\n".join(parts[:-2])  
            explanation_html = "\n\n".join(parts[-2:])  
        else:
            article_html = highlighted_html
            explanation_html = ""

        try:
            with open("explanation.txt", "w", encoding="utf-8") as f:
                f.write(explanation_html)
        except Exception as e:
            print(f"Error writing explanation.txt: {e}")

        combined_html = (
            f"<div style='font-size:14px; color:black;'>{article_html}</div>"
            f"<div style='font-size:14px; color:white;'>{explanation_html}</div>"
        )
       
        self.text_box.setHtml(combined_html)
        self.summarize_explanations()

  
    def run_slant_highlight(self, article_text):
        client = OpenAI()
        prompt = (
            "You are given an article. Identify two specific phrases that represent slant.\n"
            "Highlight them in the full text using this format:\n"
            "- Wrap each paragraph in <p> tags.\n"
            "- For each slant phrase, wrap it with this HTML span:\n"
            "  <span style='color:#DAA520; font-weight:bold;'>phrase</span>\n\n"
            "After the full article, add **two blank lines**.\n"
            "Then, provide an explanation for each highlighted phrase in the following format:\n\n"
            "Phrase: \n"
            "Explanation of why it's an example of slant.\n\n"
            "Separate each explanation with a single blank line.\n"
            "Return ONLY valid HTML that includes the full article (with highlighted phrases in <span style='color:goldenrod'>goldenrod</span>) "
            "and the list of formatted explanations underneath.\n"
            "Do not include any extra text or markdown outside of the HTML.\n\n"
            "Article:\n" + article_text
        )

        chat = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="gpt-4o-mini",
            max_tokens=3000,
        )

        html = chat.choices[0].message.content

        return html

    def highlight_slant(self):
        if not hasattr(self, 'article_text'):
            self.text_box.setText("Article not loaded.")
            return

        self.text_box.setText("Highlighting slant...")
        QApplication.processEvents()

        highlighted_html = self.run_slant_highlight(self.article_text)
        highlighted_html = re.sub(r"^```(?:html)?\s*", "", highlighted_html.strip())
        highlighted_html = re.sub(r"\s*```$", "", highlighted_html)

        parts = highlighted_html.strip().split("\n\n")
        if len(parts) > 1:
            article_html = "\n\n".join(parts[:-2])  
            explanation_html = "\n\n".join(parts[-2:])  
        else:
            article_html = highlighted_html
            explanation_html = ""

        try:
            with open("explanation.txt", "w", encoding="utf-8") as f:
                f.write(explanation_html)
        except Exception as e:
            print(f"Error writing explanation.txt: {e}")

        combined_html = (
            f"<div style='font-size:14px; color:black;'>{article_html}</div>"
            f"<div style='font-size:14px; color:white;'>{explanation_html}</div>"
        )
       
        self.text_box.setHtml(combined_html)
        self.summarize_explanations()

    def run_coverage_depth_highlight(self, article_text):
        client = OpenAI()
        prompt = (
            "You are given an article. Identify two specific phrases that represent coverage depth.\n"
            "Highlight them in the full text using this format:\n"
            "- Wrap each paragraph in <p> tags.\n"
            "- For each coverage depth phrase, wrap it with this HTML span:\n"
            "  <span style='color:#FF8C00; font-weight:bold;'>phrase</span>\n\n"
            "After the full article, add **two blank lines**.\n"
             "Then, provide an explanation for each highlighted phrase in the following format:\n\n"
            "Phrase: \n" 
            "Explanation of why it's an example of coverage depth.\n\n"
            "Separate each explanation with a single blank line.\n"
            "Return ONLY valid HTML that includes the full article (with highlighted phrases in <span style='color:orange'>orange</span>) "
            "and the list of formatted explanations underneath.\n"
            "Do not include any extra text or markdown outside of the HTML.\n\n"
            "Article:\n" + article_text
        )
        

        chat = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="gpt-4o-mini",
            max_tokens=3000,
        )

        html = chat.choices[0].message.content

        return html
    
    def highlight_coverage_depth(self):
        if not hasattr(self, 'article_text'):
            self.text_box.setText("Article not loaded.")
            return

        self.text_box.setText("Highlighting coverage depth...")
        QApplication.processEvents()

        highlighted_html = self.run_coverage_depth_highlight(self.article_text)
        highlighted_html = re.sub(r"^```(?:html)?\s*", "", highlighted_html.strip())
        highlighted_html = re.sub(r"\s*```$", "", highlighted_html)

        parts = highlighted_html.strip().split("\n\n")
        if len(parts) > 1:
            article_html = "\n\n".join(parts[:-2])  
            explanation_html = "\n\n".join(parts[-2:])  
        else:
            article_html = highlighted_html
            explanation_html = ""

        try:
            with open("explanation.txt", "w", encoding="utf-8") as f:
                f.write(explanation_html)
        except Exception as e:
            print(f"Error writing explanation.txt: {e}")

        combined_html = (
            f"<div style='font-size:14px; color:black;'>{article_html}</div>"
            f"<div style='font-size:14px; color:white;'>{explanation_html}</div>"
        )
       
        self.text_box.setHtml(combined_html)
        self.summarize_explanations()
    def summarize_explanations(self):
        try:
            with open("explanation.txt", "r", encoding="utf-8") as f:
                explanation_text = f.read()
        except Exception as e:
            self.explanation_summary_box.setText(f"Failed to load explanation.txt: {e}")
            return

        if not explanation_text.strip():
            self.explanation_summary_box.setText("No explanation text available.")
            return

        client = OpenAI()
        prompt = (
            "You are given a block of text that includes phrases and their bias explanations. "
            "Reformat the output into valid HTML where each phrase is bolded, followed by its explanation. "
            "Use the following format:\n\n"
            "Phrase: Explanation\n\n"
            "Separate each pair with a single blank line. Return ONLY valid HTML. Do not return a list, dictionary, markdown, or code block.\n\n"
            "Input:\n" + explanation_text
        )

        chat = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="gpt-4o-mini",
            max_tokens=500,
        )

        formatted_output = chat.choices[0].message.content.strip()
        self.explanation_summary_box.setHtml(formatted_output)

class BiasDetectionApp(QWidget):
    def __init__(self, stacked_widget, annotated_view):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.annotated_view = annotated_view

        self.setStyleSheet("background-color: #a3b1c6;")
        self.setMinimumSize(1400, 900)
        self.current_pdf_path = None
        self.trigger_phrases = []

        font_id = QFontDatabase.addApplicationFont("Roboto-ExtraBold.ttf")
        if font_id != -1:
            font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
            roboto_bold = QFont(font_family, 16)
        else:
            roboto_bold = QFont("Arial", 16, QFont.Bold)

        self.roboto_bold = roboto_bold

        header_label = QLabel("Bias Detector")
        header_label.setFont(QFont("Comic Sans MS", 28, QFont.Bold))
        header_label.setAlignment(Qt.AlignCenter)
        header_label.setStyleSheet("""
            color: black;
            margin-top: 20px;
            margin-bottom: 10px;
            border: 2px solid white;
            border-radius: 10px;
            padding: 10px;
            background-color: #e0e0e0;
        """)

        self.import_button = QPushButton("Import File")
        self.import_button.setFont(roboto_bold)
        self.import_button.setStyleSheet("""
            QPushButton {
                border: 2px solid white;
                border-radius: 8px;
                color: white;
                background-color: #444444;
                font-weight: bold;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #666666;
            }
        """)
        description_box = QLabel("""
        This is a bias detection program which reads a PDF file and extracts the key bias seen throughout it.<br>
        To begin, input a PDF file on the right and use the buttons below to interact with the program.
        """)
        description_box.setAlignment(Qt.AlignCenter)
        description_box.setWordWrap(True)
        description_box.setStyleSheet("""
            background-color: #e0e0e0;
            color: black;
            border: 2px solid white;
            border-radius: 10px;
            padding: 10px;
            font-size: 14px;
            margin-bottom: 15px;
        """)
        self.import_button.setFixedSize(120, 40)
        self.import_button.clicked.connect(self.select_file)

        self.filename_label = QLabel("")
        self.filename_label.setFont(QFont(self.roboto_bold.family(), 12))
        self.filename_label.setStyleSheet("color: black;")
        self.filename_label.setAlignment(Qt.AlignCenter)

        import_layout = QVBoxLayout()
        import_layout.addWidget(self.import_button)
        import_layout.addWidget(self.filename_label)

        top_layout = QHBoxLayout()
        top_layout.addStretch()
        top_layout.addLayout(import_layout)

        box_style = """
            QWidget {
                border: 2px solid white;
                border-radius: 10px;
                padding: 8px;
            }
        """

        button_style = """
            QPushButton {
                color: black;
                background-color: lightgray;
                padding: 6px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #b0b0b0;
            }
            QPushButton:pressed {
                background-color: #909090;
            }
        """

        self.analysis_box = QTextEdit()
        self.analysis_box.setReadOnly(True)
        self.analysis_box.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        analysis_layout = QVBoxLayout()
        analysis_button = QPushButton("Bias Analysis")
        analysis_button.setFont(roboto_bold)
        analysis_button.setStyleSheet(button_style)
        analysis_button.clicked.connect(self.run_analysis)
        analysis_layout.addWidget(analysis_button)
        analysis_layout.addWidget(self.analysis_box)
        analysis_widget = QWidget()
        analysis_widget.setLayout(analysis_layout)
        analysis_widget.setStyleSheet(box_style)

        self.score_box = QTextEdit()
        self.score_box.setReadOnly(True)
        score_layout = QVBoxLayout()
        score_button = QPushButton("Bias Score")
        score_button.setFont(roboto_bold)
        score_button.setStyleSheet(button_style)
        score_button.clicked.connect(self.run_score)
        score_layout.addWidget(score_button)
        score_layout.addWidget(self.score_box)
        score_widget = QWidget()
        score_widget.setLayout(score_layout)
        score_widget.setStyleSheet(box_style)

        self.triggers_box = QTextEdit()
        self.triggers_box.setReadOnly(True)
        triggers_layout = QVBoxLayout()
        triggers_button = QPushButton("Trigger Phrases Found")
        triggers_button.setFont(roboto_bold)
        triggers_button.setStyleSheet(button_style)
        triggers_button.clicked.connect(self.run_triggers)
        triggers_layout.addWidget(triggers_button)
        triggers_layout.addWidget(self.triggers_box)
        triggers_widget = QWidget()
        triggers_widget.setLayout(triggers_layout)
        triggers_widget.setStyleSheet(box_style)

        self.image_scroll = QScrollArea()
        self.image_container = QVBoxLayout()
        image_widget_inner = QWidget()
        image_widget_inner.setLayout(self.image_container)
        self.image_scroll.setWidget(image_widget_inner)
        self.image_scroll.setWidgetResizable(True)
        self.image_scroll.setFrameShape(QFrame.StyledPanel)

        image_layout = QVBoxLayout()
        image_button = QPushButton("Image Analysis")
        image_button.setFont(roboto_bold)
        image_button.setStyleSheet(button_style)
        image_button.clicked.connect(self.run_images)
        image_layout.addWidget(image_button)
        image_layout.addWidget(self.image_scroll)
        image_widget = QWidget()
        image_widget.setLayout(image_layout)
        image_widget.setStyleSheet(box_style)

        middle_splitter = QSplitter(Qt.Horizontal)
        middle_splitter.addWidget(analysis_widget)
        middle_splitter.addWidget(score_widget)

        bottom_splitter = QSplitter(Qt.Horizontal)
        bottom_splitter.addWidget(image_widget)
        bottom_splitter.addWidget(triggers_widget)
        bottom_splitter.setSizes([800, 400])

        main_splitter = QSplitter(Qt.Vertical)
        main_splitter.addWidget(middle_splitter)
        main_splitter.addWidget(bottom_splitter)
        main_splitter.setSizes([500, 400])

        self.view_annotated_button = QPushButton("See Document Annotations")
        self.view_annotated_button.setFont(QFont(self.roboto_bold.family(), 14))
        self.view_annotated_button.setStyleSheet("""
            QPushButton {
                background-color: #dddddd;
                border-radius: 8px;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #cccccc;
            }
        """)
        self.view_annotated_button.setEnabled(False)
        self.view_annotated_button.clicked.connect(self.open_annotated_window)

        main_layout = QVBoxLayout()
        main_layout.addWidget(header_label)
        main_layout.addWidget(description_box)
        main_layout.addLayout(top_layout)
        main_layout.addWidget(main_splitter)
        main_layout.addWidget(self.view_annotated_button, alignment=Qt.AlignCenter)
        self.setLayout(main_layout)

    def open_annotated_window(self):
        if not os.path.exists("article.txt"):
            return
        self.annotated_view.load_article("article.txt")
        self.stacked_widget.setCurrentIndex(1)

    def select_file(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Select File", "", "PDF and Image Files (*.pdf *.jpg *.jpeg)"
        )
        if filepath:
            self.current_pdf_path = filepath
            filename = os.path.basename(filepath)
            self.import_button.setText("Imported")
            self.filename_label.setText(filename)

    def clear_images(self):
        while self.image_container.count():
            child = self.image_container.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def run_analysis(self):
        if not self.current_pdf_path:
            self.analysis_box.setText("Please import a file first.")
            return
        text = extract_text(self.current_pdf_path)
        with open("article.txt", "w") as f:
            f.write(text)
        with open("article.txt", "r") as f:
            content = f.read()
        self.analysis_box.setText("Running bias analysis...")
        QApplication.processEvents()
        self.analysis_result = run_analysis(content)
        self.analysis_box.setText(self.analysis_result)
        self.view_annotated_button.setEnabled(True)

    def run_score(self):
        if not hasattr(self, "analysis_result"):
            self.score_box.setText("Run analysis first.")
            return
        with open("article.txt", "r") as f:
            content = f.read()
        self.score_box.setText("Scoring bias...")
        QApplication.processEvents()
        score = run_score(self.analysis_result, content)
        self.score_box.setHtml(score)


    def run_triggers(self):
        if not hasattr(self, "analysis_result"):
            self.triggers_box.setText("Run analysis first.")
            return
        with open("article.txt", "r") as f:
            content = f.read()
        self.triggers_box.setText("Extracting trigger phrases...")
        QApplication.processEvents()
        trigger_output = run_triggers(content, self.analysis_result)
        self.triggers_box.setHtml(trigger_output)


    def run_images(self):
        if not self.current_pdf_path:
            return
        self.clear_images()
        cleanup_extracted_images()
        QApplication.processEvents()
        images = run_image_analysis(self.current_pdf_path)

        if not images:
            no_image_label = QLabel("No image found.")
            no_image_label.setFont(self.roboto_bold)
            no_image_label.setStyleSheet("margin: 10px; color: black;")
            self.image_container.addWidget(no_image_label)
            return

        for path, summary in images:
            img_label = QLabel()
            pixmap = QPixmap(path).scaledToWidth(300, Qt.SmoothTransformation)
            img_label.setPixmap(pixmap)
            summary_label = QLabel(summary)
            summary_label.setWordWrap(True)
            summary_label.setFont(self.roboto_bold)
            summary_label.setStyleSheet("margin-bottom: 15px;")
            self.image_container.addWidget(img_label)
            self.image_container.addWidget(summary_label)



def run_analysis(file_content):
    load_dotenv()
    client = OpenAI()
    prompt = (
        "Analyze the following article for these bias categories:\n"
        "Narrative Bias, Sentiment Bias, Regional Bias, Slant, and Coverage Depth.\n\n"
        "Use only HTML formatting. For each section:\n"
        "- Wrap the explanation in a <p> tag.\n"
        "- Start with a <b> tag containing the category name, but color the header like so:\n"
        "  • Narrative Bias: <span style='color:#1E90FF;'> (blue)\n"
        "  • Sentiment Bias: <span style='color:#FF4500;'> (red-orange)\n"
        "  • Regional Bias: <span style='color:#228B22;'> (green)\n"
        "  • Slant: <span style='color:#DAA520;'> (goldenrod)\n"
        "  • Coverage Depth: <span style='color:#FF8C00;'> (orange)\n"
        "- Close the colored span and bold tag, and follow it with the analysis text.\n\n"
        "Example:\n"
        "<p><b><span style='color:#1E90FF;'>Narrative Bias:</span></b> This article uses a compelling 'us vs. them' story...</p>\n"
        "<p><b><span style='color:#FF4500;'>Sentiment Bias:</span></b> The wording is emotionally charged...</p>\n"
        "...and so on.\n\n"
        "Do not use Markdown. Only return valid HTML.\n\n"
        "Article:\n" + file_content
    )
    chat = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="gpt-4o-mini",
        max_tokens=650,
    )
    return chat.choices[0].message.content


def run_score(analysis, file_content):
    client = OpenAI()
    prompt = (
        "You are formatting an HTML block of text to display in a PyQt application.\n"
        "Based on the analysis below, give a bias score out of 10 (10 = extremely biased), and provide a short summary explaining why.\n\n"
        "Strict formatting instructions:\n"
        "- Wrap the score line in a <p> tag, starting with <b>Score:</b> followed by the score (e.g., 6/10).\n"
        "- Wrap the summary explanation in a separate <p> tag.\n"
        "- Use ONLY HTML. Do NOT use Markdown or raw text formatting.\n"
        "- Do NOT write anything before or after the <p> blocks.\n\n"
        "Example:\n"
        "<p><b>Score:</b> 7/10</p>\n<p>The article uses emotionally charged language to present a one-sided view...</p>\n\n"
        "Now generate the output.\n\n"
        "Analysis:\n" + analysis + "\n\nArticle:\n" + file_content
    )

    chat = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="gpt-4o-mini",
        max_tokens=650,
    )

    response = chat.choices[0].message.content.strip()

    # Extract the score from the first <p> tag
    match = re.search(r"<p><b>Score:</b>\s*(\d+)/10</p>", response)
    if match:
        score = int(match.group(1))
        color = "red" if score >= 5 else "green"
        colored_score_html = f"<p><b>Score:</b> <span style='color:{color};'>{score}/10</span></p>"
        # Replace the plain score line with colored version
        response = re.sub(r"<p><b>Score:</b>\s*\d+/10</p>", colored_score_html, response)

    return response


def run_triggers(file_content, analysis):
    client = OpenAI()
    prompt = (
    "You are formatting an HTML block to display trigger phrases in a PyQt application.\n"
    "Identify 3 trigger phrases that support the bias analysis below, and include the paragraph number for each.\n\n"
    "Strict formatting instructions:\n"
    "- Use ONLY HTML.\n"
    "- For each phrase, wrap the output in a <p> tag.\n"
    "- Bold the phrase label using <b>Trigger Phrase:</b> and bold the paragraph label with <b>Paragraph:</b>.\n"
    "- Do NOT use Markdown (**bold**) or raw text formatting.\n"
    "- Do NOT write anything outside the <p> blocks.\n\n"
    "Example:\n"
    "<p><b>Trigger Phrase:</b> 'They always lie to the people.'<br><b>Paragraph:</b> 3</p>\n"
    "<p><b>Trigger Phrase:</b> 'A corrupt cabal controls the media.'<br><b>Paragraph:</b> 6</p>\n"
    "<p><b>Trigger Phrase:</b> 'Voices of reason are silenced.'<br><b>Paragraph:</b> 8</p>\n\n"
    "Now extract trigger phrases based on this analysis:\n" + analysis +
    "\n\nFrom this article:\n" + file_content
    )   
    chat = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="gpt-4o-mini",
        max_tokens=300,
    )
    triggers = chat.choices[0].message.content

    # Save to file so annotated view can use it
    with open("trigger_phrases.txt", "w") as f:
        f.write(triggers)

    return triggers


def run_annotated_highlighted_article(article_text, trigger_text):
    client = OpenAI()
    prompt = (
        "Highlight the specific trigger phrases listed below in purple, bold text inside the article.\n\n"
        "Trigger Phrases:\n" + trigger_text + "\n\n"
        "Instructions:\n"
        "- Wrap each paragraph of the article in a <p> tag.\n"
        "- Within paragraphs, wrap each trigger phrase in this HTML span:\n"
        "  <span style='color:purple; font-weight:bold;'>trigger phrase</span>\n"
        "- Only modify exact phrases from the trigger list. Keep everything else unchanged.\n"
        "- Use ONLY valid HTML and do not include explanations or intros.\n\n"
        "- Exclude any unecessary text and just use the main paragraphs in the article. \n"
        "Article:\n" + article_text
    )
    chat = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="gpt-4o-mini",
        max_tokens=3000,
    )
    return chat.choices[0].message.content



def run_image_analysis(pdf_path):
    client = OpenAI()
    result_blocks = []
    prompt = "Briefly describe in 2-3 sentences how this image relates to the bias detected."
    pdf = fitz.open(pdf_path)
    counter = 1
    for i in range(len(pdf)):
        images = pdf[i].get_images()
        for image in images:
            base_img = pdf.extract_image(image[0])
            image_data = base_img["image"]
            img = PIL.Image.open(io.BytesIO(image_data))
            ext = base_img["ext"]
            img_path = f"image{counter}.{ext}"
            img.save(img_path)
            b64 = base64.b64encode(open(img_path, "rb").read()).decode("utf-8")
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/{ext};base64,{b64}"}}
                    ]
                }],
                max_tokens=200,
            )
            summary = response.choices[0].message.content.strip()
            result_blocks.append((img_path, summary))
            counter += 1
    return result_blocks


def cleanup_extracted_images():
    for filename in os.listdir():
        if filename.lower().startswith("image") and filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".tiff")):
            try:
                os.remove(filename)
            except Exception as e:
                print(f"Could not delete {filename}: {e}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    stacked_widget = QStackedWidget()
    annotated_view = AnnotatedDocumentWindow(stacked_widget)
    main_view = BiasDetectionApp(stacked_widget, annotated_view)
    stacked_widget.addWidget(main_view)
    stacked_widget.addWidget(annotated_view)
    stacked_widget.setCurrentIndex(0)
    stacked_widget.show()
    sys.exit(app.exec_())
