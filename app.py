import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.auth import (
    PASSWORD_MAX_LENGTH,
    PASSWORD_MIN_LENGTH,
    UsernameAlreadyExistsError,
    authenticate_user,
    initialize_database,
    register_user,
)
from src.analyzer import analyze_pdf, compare_analyses, render_report


st.set_page_config(
    page_title="AI Contract Risk Analyzer",
    page_icon="⚖️",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp {
        background: #f5f7fb;
    }
    .block-container {
        max-width: 1440px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }
    [data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e6eaf2;
        border-radius: 14px;
        padding: 18px 20px;
        box-shadow: 0 3px 12px rgba(27, 39, 68, 0.04);
    }
    [data-testid="stMetricLabel"] {
        color: #64748b;
    }
    [data-testid="stMetricValue"] {
        color: #172554;
    }
    div[data-testid="stExpander"] {
        background: #ffffff;
        border: 1px solid #e6eaf2;
        border-radius: 12px;
    }
    .welcome-card {
        background: #ffffff;
        border: 1px solid #e6eaf2;
        border-radius: 16px;
        padding: 28px;
        box-shadow: 0 8px 26px rgba(27, 39, 68, 0.06);
    }
    .welcome-eyebrow {
        color: #5274d9;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        font-size: 0.8rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def render_sign_in_page():
    st.markdown(
        """
        <div class="welcome-card">
          <div class="welcome-eyebrow">Contract review workspace</div>
          <h1>Review agreements with greater clarity.</h1>
          <p>AI Contract Risk Analyzer gives you a structured first pass over searchable PDF agreements.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")

    intro_col, login_col = st.columns([1.15, 0.85], gap="large")
    with intro_col:
        st.subheader("What this workspace does")
        st.markdown(
            "- Extracts likely payment, termination, and renewal passages with page references.\n"
            "- Highlights selected wording patterns and items that may need review.\n"
            "- Compares two versions to show detected clause and risk-flag changes."
        )
        st.info(
            "This is a rule-based decision-support tool, not a trained legal AI "
            "system. It does not provide legal advice or determine whether a "
            "contract is enforceable."
        )
        st.caption(
            "PDFs are analyzed in this app session. Upload searchable PDFs; "
            "scanned documents may require OCR."
        )
        st.caption(
            "Account creation is open to anyone with access to this app. "
            "There is no email verification or password recovery."
        )

    with login_col:
        access_mode = st.radio(
            "Account access",
            ["Sign in", "Create account"],
            horizontal=True,
            label_visibility="collapsed",
        )
        st.subheader(access_mode)

        if access_mode == "Sign in":
            with st.form("sign_in_form"):
                username = st.text_input("Username", autocomplete="username")
                password = st.text_input(
                    "Password",
                    type="password",
                    max_chars=PASSWORD_MAX_LENGTH,
                    autocomplete="current-password",
                )
                submitted = st.form_submit_button(
                    "Sign in", use_container_width=True
                )

            if submitted:
                if authenticate_user(username, password):
                    st.session_state["authenticated"] = True
                    st.session_state["username"] = username.strip().lower()
                    st.rerun()
                st.error("The username or password is incorrect.")
        else:
            st.caption(
                f"Open registration. Passwords must be at least "
                f"{PASSWORD_MIN_LENGTH} characters."
            )
            with st.form("create_account_form"):
                username = st.text_input(
                    "Choose a username",
                    max_chars=32,
                    autocomplete="username",
                    help="3 to 32 letters, numbers, periods, underscores, or hyphens.",
                )
                password = st.text_input(
                    "Create a password",
                    type="password",
                    max_chars=PASSWORD_MAX_LENGTH,
                    autocomplete="new-password",
                )
                confirmation = st.text_input(
                    "Confirm password",
                    type="password",
                    max_chars=PASSWORD_MAX_LENGTH,
                    autocomplete="new-password",
                )
                submitted = st.form_submit_button(
                    "Create account", type="primary", use_container_width=True
                )

            if submitted:
                if password != confirmation:
                    st.error("The passwords do not match.")
                else:
                    try:
                        account_name = register_user(username, password)
                    except UsernameAlreadyExistsError as exc:
                        st.error(str(exc))
                    except ValueError as exc:
                        st.error(str(exc))
                    else:
                        st.session_state["authenticated"] = True
                        st.session_state["username"] = account_name
                        st.rerun()


def render_signed_out_page():
    st.markdown(
        """
        <div class="welcome-card">
          <div class="welcome-eyebrow">Session ended</div>
          <h1>You are signed out.</h1>
          <p>Your analysis workspace is no longer available in this session.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Return to sign in", type="primary"):
        st.session_state["auth_page"] = "sign_in"
        st.rerun()


def sign_out():
    st.session_state.clear()
    st.session_state["auth_page"] = "signed_out"


def render_application():
    title_col, account_col = st.columns([4, 1])
    with title_col:
        st.title("⚖️ AI Contract Risk Analyzer")
        st.caption("A clear, at-a-glance view of detected clauses and review points.")
    with account_col:
        st.caption(f"Signed in as **{st.session_state['username']}**")
        if st.button("Sign out", use_container_width=True):
            sign_out()
            st.rerun()

    st.warning(
        "Decision-support prototype only. It does not provide legal advice, "
        "determine enforceability, or guarantee that every clause has been "
        "detected. Have a qualified lawyer review important agreements."
    )

    tabs = st.tabs(["Analyze one contract", "Compare two contracts"])
    with tabs[0]:
        uploaded = st.file_uploader(
            "Upload an agreement PDF",
            type=["pdf"],
            key="single",
            help="Upload a searchable PDF to build its risk and clause dashboard.",
        )
        if uploaded:
            try:
                result = analyze_pdf(uploaded.getvalue(), uploaded.name)
                render_analysis_dashboard(result)
            except Exception as exc:
                st.error(f"Could not analyze this PDF: {exc}")

    with tabs[1]:
        left, right = st.columns(2)
        with left:
            pdf_a = st.file_uploader(
                "Upload original contract (PDF)", type=["pdf"], key="compare_a"
            )
        with right:
            pdf_b = st.file_uploader(
                "Upload revised contract (PDF)", type=["pdf"], key="compare_b"
            )
        if pdf_a and pdf_b:
            try:
                result_a = analyze_pdf(pdf_a.getvalue(), pdf_a.name)
                result_b = analyze_pdf(pdf_b.getvalue(), pdf_b.name)
                diff = compare_analyses(result_a, result_b)
                render_comparison_dashboard(
                    result_a, result_b, diff, pdf_a.name, pdf_b.name
                )
            except Exception as exc:
                st.error(f"Could not compare these PDFs: {exc}")


def _severity_counts(result):
    severities = ["High", "Medium", "Low"]
    counts = {
        severity: sum(risk["severity"] == severity for risk in result["risks"])
        for severity in severities
    }
    return severities, counts


def render_analysis_dashboard(result):
    st.subheader("Contract dashboard")
    st.caption(result["filename"])

    metric_cols = st.columns(4)
    metric_cols[0].metric("Risk level", result["risk_level"])
    metric_cols[1].metric("Review flags", len(result["risks"]))
    metric_cols[2].metric("Key passages", sum(
        len(entries) for entries in result["clauses"].values()
    ))
    metric_cols[3].metric("Items to verify", len(result["missing"]))

    st.markdown("#### Executive summary")
    st.info(result["summary"])

    chart_cols = st.columns(2)
    severity_order, severity_data = _severity_counts(result)
    severity_labels = severity_order
    severity_values = [severity_data[label] for label in severity_order]
    severity_colors = ["#dc5a5a", "#f0a43c", "#e7c84b"]
    if not result["risks"]:
        severity_labels = ["No detected flags"]
        severity_values = [1]
        severity_colors = ["#cbd5e1"]

    severity_chart = go.Figure(
        data=[
            go.Pie(
                labels=severity_labels,
                values=severity_values,
                hole=0.62,
                sort=False,
                marker=dict(colors=severity_colors, line=dict(color="#ffffff", width=3)),
                textinfo="label" if not result["risks"] else "label+value",
                hovertemplate="%{label}: %{value}<extra></extra>",
            )
        ]
    )
    severity_chart.update_layout(
        title="Detected flags by severity",
        showlegend=True,
        legend=dict(orientation="h", y=-0.12),
        margin=dict(t=55, b=35, l=10, r=10),
        height=340,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#334155"),
    )
    severity_chart.add_annotation(
        text=f"<b>{len(result['risks'])}</b><br>flags",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=19, color="#172554"),
    )

    clause_labels = ["Payment", "Termination", "Renewal"]
    clause_keys = ["payment", "termination", "renewal"]
    clause_counts = [len(result["clauses"].get(key, [])) for key in clause_keys]
    clause_chart = px.bar(
        x=clause_counts,
        y=clause_labels,
        orientation="h",
        text=clause_counts,
        labels={"x": "Detected passages", "y": ""},
        color_discrete_sequence=["#5274d9"],
    )
    clause_chart.update_traces(
        textposition="outside",
        cliponaxis=False,
        hovertemplate="%{y}: %{x} passage(s)<extra></extra>",
    )
    clause_chart.update_layout(
        title="Key clause passages",
        showlegend=False,
        xaxis=dict(dtick=1, rangemode="tozero", gridcolor="#e8edf5"),
        yaxis=dict(autorange="reversed"),
        margin=dict(t=55, b=35, l=10, r=25),
        height=340,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#334155"),
    )

    with chart_cols[0]:
        st.plotly_chart(severity_chart, use_container_width=True)
    with chart_cols[1]:
        st.plotly_chart(clause_chart, use_container_width=True)

    st.markdown("#### Key clauses")
    for key, label in [
        ("payment", "Payment"),
        ("termination", "Termination"),
        ("renewal", "Renewal"),
    ]:
        with st.expander(f"{label} ({len(result['clauses'].get(key, []))} passages)"):
            entries = result["clauses"].get(key, [])
            if entries:
                for entry in entries:
                    st.markdown(f'**Page {entry["page"]}**')
                    st.write(entry["text"])
            else:
                st.warning(
                    f"No likely {label.lower()} clause was detected. "
                    "This may be absent or phrased differently."
                )

    st.markdown("#### Potential risks and review points")
    if result["risks"]:
        for item in result["risks"]:
            with st.expander(f'{item["severity"]} — {item["title"]}', expanded=True):
                st.write(item["detail"])
                st.caption(f'Basis: {item["basis"]}')
    else:
        st.success(
            "No rule-based flags were triggered. This is not proof that the "
            "contract is risk-free."
        )

    st.markdown("#### Missing or unclear items to verify")
    if result["missing"]:
        for item in result["missing"]:
            st.markdown(f"- {item}")
    else:
        st.success("No missing items were identified by the current checks.")

    st.download_button(
        "Download analysis report (Markdown)",
        render_report(result),
        file_name="contract_risk_report.md",
        mime="text/markdown",
    )


def render_comparison_dashboard(original, revised, diff, original_name, revised_name):
    st.subheader("Comparison dashboard")
    st.caption(f"{original_name}  →  {revised_name}")

    metric_cols = st.columns(4)
    metric_cols[0].metric("Changed sections", len(diff["changes"]))
    metric_cols[1].metric("Original flags", len(original["risks"]))
    metric_cols[2].metric("Revised flags", len(revised["risks"]))
    metric_cols[3].metric(
        "Risk flag change",
        len(revised["risks"]) - len(original["risks"]),
        delta_color="inverse",
    )

    chart_cols = st.columns(2)
    severities = ["High", "Medium", "Low"]
    _, original_counts = _severity_counts(original)
    _, revised_counts = _severity_counts(revised)
    risk_chart = go.Figure()
    risk_chart.add_trace(
        go.Bar(
            name="Original",
            x=severities,
            y=[original_counts[level] for level in severities],
            marker_color="#94a3b8",
        )
    )
    risk_chart.add_trace(
        go.Bar(
            name="Revised",
            x=severities,
            y=[revised_counts[level] for level in severities],
            marker_color="#5274d9",
        )
    )
    risk_chart.update_layout(
        title="Risk flags by severity",
        barmode="group",
        yaxis=dict(dtick=1, rangemode="tozero", gridcolor="#e8edf5"),
        margin=dict(t=55, b=35, l=10, r=10),
        height=340,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#334155"),
        legend=dict(orientation="h", y=-0.2),
    )

    change_counts = {"Added": 0, "Changed": 0, "Removed": 0}
    for change in diff["changes"]:
        change_counts[change["status"]] = change_counts.get(change["status"], 0) + 1
    change_labels = [label for label, count in change_counts.items() if count]
    change_values = [change_counts[label] for label in change_labels]
    if not change_labels:
        change_labels = ["No detected changes"]
        change_values = [1]
    change_colors = {
        "Added": "#45a987",
        "Changed": "#5274d9",
        "Removed": "#dc5a5a",
        "No detected changes": "#cbd5e1",
    }
    change_chart = go.Figure(
        data=[
            go.Pie(
                labels=change_labels,
                values=change_values,
                hole=0.58,
                sort=False,
                marker=dict(
                    colors=[change_colors[label] for label in change_labels],
                    line=dict(color="#ffffff", width=3),
                ),
                textinfo=(
                    "label"
                    if "No detected changes" in change_labels
                    else "label+value"
                ),
                hovertemplate="%{label}: %{value}<extra></extra>",
            )
        ]
    )
    change_chart.update_layout(
        title="Detected clause changes",
        showlegend=True,
        legend=dict(orientation="h", y=-0.12),
        margin=dict(t=55, b=35, l=10, r=10),
        height=340,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#334155"),
    )

    with chart_cols[0]:
        st.plotly_chart(risk_chart, use_container_width=True)
    with chart_cols[1]:
        st.plotly_chart(change_chart, use_container_width=True)

    st.markdown("#### Extracted clause changes")
    if diff["changes"]:
        for change in diff["changes"]:
            with st.expander(f'{change["section"]}: {change["status"]}', expanded=True):
                before_col, after_col = st.columns(2)
                with before_col:
                    st.markdown("**Original**")
                    st.write(change["before"] or "No likely clause detected.")
                with after_col:
                    st.markdown("**Revised**")
                    st.write(change["after"] or "No likely clause detected.")
    else:
        st.info("No differences were found in the extracted key-clause text.")

    st.markdown("#### Risk flag changes")
    for line in diff["risk_changes"]:
        st.markdown(f"- {line}")

    st.download_button(
        "Download comparison report (Markdown)",
        diff["markdown"],
        file_name="contract_comparison.md",
        mime="text/markdown",
    )


initialize_database()
if st.session_state.get("authenticated", False):
    render_application()
elif st.session_state.get("auth_page") == "signed_out":
    render_signed_out_page()
else:
    render_sign_in_page()
