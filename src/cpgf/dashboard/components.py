from __future__ import annotations

import streamlit as st

NAVY = "#0B1F3A"
BLUE = "#315C87"
SLATE = "#5F6B7A"
ORANGE = "#E67E22"
LIGHT = "#F4F6F8"
BORDER = "#DDE3EA"


def apply_page_style() -> None:
    st.markdown(
        f"""
        <style>
        .stApp {{
            background: #FFFFFF;
        }}
        [data-testid="stSidebar"] {{
            background: {LIGHT};
            border-right: 1px solid {BORDER};
        }}
        h1, h2, h3 {{
            color: {NAVY};
            letter-spacing: -0.02em;
        }}
        .cpgf-kicker {{
            color: {BLUE};
            font-weight: 700;
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 0.25rem;
        }}
        .cpgf-subtitle {{
            color: {SLATE};
            font-size: 1.02rem;
            max-width: 900px;
            margin-bottom: 1.2rem;
        }}
        .cpgf-callout {{
            border-left: 4px solid {ORANGE};
            background: #FFF8F1;
            padding: 0.85rem 1rem;
            border-radius: 0 8px 8px 0;
            color: #3B4652;
            margin: 0.8rem 0 1.2rem 0;
        }}
        .cpgf-neutral {{
            border: 1px solid {BORDER};
            background: #FAFBFC;
            padding: 0.85rem 1rem;
            border-radius: 8px;
            color: #3B4652;
        }}
        [data-testid="stMetric"] {{
            border: 1px solid {BORDER};
            background: #FFFFFF;
            padding: 0.9rem;
            border-radius: 10px;
            box-shadow: 0 1px 3px rgba(11,31,58,0.04);
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str, *, kicker: str = "CPGF · Controle Social") -> None:
    st.markdown(f'<div class="cpgf-kicker">{kicker}</div>', unsafe_allow_html=True)
    st.title(title)
    st.markdown(f'<div class="cpgf-subtitle">{subtitle}</div>', unsafe_allow_html=True)


def render_disclaimer() -> None:
    st.markdown(
        """
        <div class="cpgf-callout">
        <strong>Como interpretar.</strong> Os resultados são sinais, indicadores e condições
        para verificação. Não constituem conclusão automática de fraude, irregularidade ou
        fracionamento de despesa.
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_partial_period_note(year_end: int) -> None:
    if int(year_end) >= 2026:
        st.caption(
            "2026 é período parcial no snapshot canônico (dados disponíveis até julho). "
            "Comparações anuais devem considerar essa diferença de exposição."
        )


def style_plotly(fig, *, height: int = 390, legend: bool = True):
    fig.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=45, b=20),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(color="#263442"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        showlegend=legend,
    )
    fig.update_xaxes(showgrid=False, linecolor="#DDE3EA")
    fig.update_yaxes(gridcolor="#EEF1F4", zeroline=False)
    return fig


def unavailable_state(message: str) -> None:
    st.warning(
        "A camada analítica não pôde ser inicializada neste ambiente. "
        f"Detalhe técnico: {message}"
    )
    st.info(
        "A interface permanece disponível, mas os gráficos dependentes do Serving 1.4.0 "
        "só são exibidos após um bootstrap íntegro."
    )
