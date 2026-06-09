"""
app.py — Milestone 5 query interface (Gradio web UI).

Run:
    python app.py
Then open http://localhost:7860
"""

import gradio as gr

from query import ask


def handle_query(question):
    if not question or not question.strip():
        return "Please enter a question.", ""
    result = ask(question)
    if result["sources"]:
        sources = "\n".join(f"• {s}" for s in result["sources"])
    else:
        sources = "(none — the system did not have enough information to answer)"
    return result["answer"], sources


EXAMPLES = [
    "What do students say about Andrew Ng's machine learning courses?",
    "How do students describe Percy Liang as a professor?",
    "Which CS professor is described as funny or like a stand-up comedian?",
    "Do any reviews mention group projects or team assignments?",
]

with gr.Blocks(title="The Unofficial Guide") as demo:
    gr.Markdown(
        "# 🎓 The Unofficial Guide\n"
        "Ask about CS professors at Stanford & Harvard. Answers come **only** from "
        "real student reviews (Rate My Professors), with sources cited."
    )
    inp = gr.Textbox(label="Your question", placeholder="e.g. Is Percy Liang a good professor?")
    btn = gr.Button("Ask", variant="primary")
    answer = gr.Textbox(label="Answer", lines=8)
    sources = gr.Textbox(label="Retrieved from", lines=4)
    gr.Examples(examples=EXAMPLES, inputs=inp)

    btn.click(handle_query, inputs=inp, outputs=[answer, sources])
    inp.submit(handle_query, inputs=inp, outputs=[answer, sources])

if __name__ == "__main__":
    demo.launch()
