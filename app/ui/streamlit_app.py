"""Minimal Streamlit authentication UI for Phase 2."""

from __future__ import annotations

import os

import requests
import streamlit as st


API_URL = os.getenv("LEARNMATE_API_URL", "http://127.0.0.1:5000").rstrip("/")


def _headers() -> dict[str, str]:
    session_id = st.session_state.get("session_id")
    return {"X-Session-ID": session_id} if session_id else {}


def _request(method: str, path: str, **kwargs):
    return requests.request(
        method, f"{API_URL}{path}", headers=_headers(), timeout=5, **kwargs
    )


def _show_auth_forms() -> None:
    register_tab, login_tab = st.tabs(["Register", "Login"])
    with register_tab:
        with st.form("register_form"):
            name = st.text_input("Name")
            email = st.text_input("Email", key="register_email")
            password = st.text_input("Password", type="password", key="register_password")
            submitted = st.form_submit_button("Register")
        if submitted:
            try:
                response = _request(
                    "POST",
                    "/api/auth/register",
                    json={"name": name, "email": email, "password": password},
                )
                if response.status_code == 201:
                    st.success("Registration completed. You can now log in.")
                else:
                    st.error(response.json().get("error", "Registration failed"))
            except requests.RequestException as exc:
                st.error(f"Registration request failed: {exc}")

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Login")
        if submitted:
            try:
                response = _request(
                    "POST",
                    "/api/auth/login",
                    json={"email": email, "password": password},
                )
                if response.status_code == 200:
                    st.session_state.session_id = response.json()["session_id"]
                    st.rerun()
                else:
                    st.error(response.json().get("error", "Login failed"))
            except requests.RequestException as exc:
                st.error(f"Login request failed: {exc}")


def _show_authenticated_state() -> None:
    try:
        response = _request("GET", "/api/auth/me")
        if response.status_code != 200:
            st.session_state.session_id = None
            st.warning("Your session has expired. Please log in again.")
            return
        student = response.json()["student"]
        st.success(f"Logged in as {student['name']}")
        st.json(student)
        if st.button("Logout"):
            _request("POST", "/api/auth/logout")
            st.session_state.session_id = None
            st.rerun()
        _show_materials()
        _show_tutor()
        _show_quizzes()
        _show_phase6()
    except requests.RequestException as exc:
        st.error(f"Session request failed: {exc}")


def _show_materials() -> None:
    st.header("Educational Materials")
    with st.form("document_upload_form"):
        uploaded_file = st.file_uploader("Select a PDF", type=["pdf"])
        title = st.text_input("Title")
        subject = st.text_input("Subject")
        submitted = st.form_submit_button("Upload material")
    if submitted:
        if uploaded_file is None:
            st.error("Select a PDF before uploading.")
        else:
            try:
                response = _request(
                    "POST",
                    "/api/documents",
                    files={
                        "file": (
                            uploaded_file.name,
                            uploaded_file.getvalue(),
                            uploaded_file.type or "application/pdf",
                        )
                    },
                    data={"title": title, "subject": subject},
                )
                if response.status_code == 201:
                    st.success("Educational material uploaded and processed.")
                else:
                    st.error(response.json().get("error", "Document upload failed"))
            except requests.RequestException as exc:
                st.error(f"Document upload request failed: {exc}")

    try:
        response = _request("GET", "/api/documents")
        if response.status_code == 200:
            documents = response.json().get("documents", [])
            for document in documents:
                with st.container(border=True):
                    st.write(f"**{document['title']}**")
                    st.caption(f"Subject: {document['subject']}")
                    if st.button("Delete", key=f"delete-document-{document['document_id']}"):
                        delete_response = _request(
                            "DELETE", f"/api/documents/{document['document_id']}"
                        )
                        if delete_response.status_code == 200:
                            st.rerun()
                        st.error(delete_response.json().get("error", "Document deletion failed"))
        elif response.status_code != 401:
            st.error(response.json().get("error", "Could not load documents"))
    except requests.RequestException as exc:
        st.error(f"Document listing request failed: {exc}")


def _show_tutor() -> None:
    st.header("Tutor")
    with st.form("tutor_query_form"):
        question = st.text_area("Ask about your uploaded materials")
        submitted = st.form_submit_button("Ask Tutor")
    if submitted:
        try:
            response = _request("POST", "/api/tutor/query", json={"question": question})
            payload = response.json()
            if response.status_code == 200:
                st.write(payload.get("response", ""))
                if payload.get("grounded") and payload.get("sources"):
                    st.caption("Sources")
                    for source in payload["sources"]:
                        st.write(
                            f"{source.get('title') or 'Uploaded material'} - "
                            f"{source.get('subject') or 'Unknown subject'} - "
                            f"page {source.get('page_number') or 'unknown'}"
                        )
            else:
                st.error(payload.get("error", "Tutor request failed"))
        except requests.RequestException as exc:
            st.error(f"Tutor request failed: {exc}")
    if st.button("Clear conversation context"):
        try:
            response = _request("DELETE", "/api/tutor/context")
            if response.status_code == 200:
                st.success("Conversation context cleared.")
            else:
                st.error(response.json().get("error", "Could not clear context"))
        except requests.RequestException as exc:
            st.error(f"Context clear request failed: {exc}")


def _show_quizzes() -> None:
    st.header("Quiz")
    with st.form("quiz_generation_form"):
        topic = st.text_input("Quiz topic")
        difficulty = st.selectbox("Difficulty", ["beginner", "intermediate", "advanced"])
        submitted = st.form_submit_button("Generate quiz")
    if submitted:
        try:
            response = _request(
                "POST", "/api/quizzes", json={"topic": topic, "difficulty": difficulty}
            )
            if response.status_code == 201:
                st.session_state.quiz = response.json()
            else:
                st.error(response.json().get("error", "Quiz generation failed"))
        except requests.RequestException as exc:
            st.error(f"Quiz generation request failed: {exc}")

    quiz = st.session_state.get("quiz")
    if quiz:
        with st.form("quiz_submission_form"):
            answers = []
            for index, question in enumerate(quiz["questions"]):
                options = question.get("options") or ["Short answer"]
                answers.append(st.radio(question["question"], options, key=f"quiz-answer-{index}"))
            submitted = st.form_submit_button("Submit quiz")
        if submitted:
            try:
                response = _request(
                    "POST",
                    f"/api/quizzes/{quiz['quiz_id']}/submit",
                    json={"answers": answers},
                )
                if response.status_code == 200:
                    st.session_state.quiz_result = response.json()
                    st.session_state.pop("quiz", None)
                else:
                    st.error(response.json().get("error", "Quiz submission failed"))
            except requests.RequestException as exc:
                st.error(f"Quiz submission request failed: {exc}")

    result = st.session_state.get("quiz_result")
    if result:
        st.success(f"Score: {result['score']}%")
        st.caption(f"{result['topic']} - {result['difficulty']}")
        try:
            response = _request("GET", "/api/quizzes/adaptive/status")
            if response.status_code == 200:
                weak_topics = [item["topic"] for item in response.json()["topics"] if item["weak"]]
                if weak_topics:
                    st.info(f"Additional study focus: {', '.join(weak_topics)}")
        except requests.RequestException as exc:
            st.error(f"Adaptive status request failed: {exc}")


def _show_phase6() -> None:
    st.header("Recommendations")
    if st.button("Generate or refresh recommendations"):
        response = _request("POST", "/api/recommendations/generate")
        if response.status_code not in (200, 201):
            st.error(response.json().get("error", "Recommendation generation failed"))
    recommendations_response = _request("GET", "/api/recommendations")
    if recommendations_response.status_code == 200:
        for item in recommendations_response.json().get("recommendations", []):
            st.write(f"**{item['topic']}**: {item['recommendation_text']}")
    adaptive_response = _request("GET", "/api/recommendations/adaptive")
    if adaptive_response.status_code == 200:
        weak_topics = [item for item in adaptive_response.json().get("topics", []) if item["weak"]]
        if weak_topics:
            st.caption("Weak topics")
            st.json(weak_topics)

    st.header("Learning Analytics")
    analytics_response = _request("GET", "/api/analytics")
    if analytics_response.status_code == 200:
        analytics = analytics_response.json()["analytics"]
        st.metric("Evaluated quizzes", analytics["total_evaluated_quizzes"])
        st.metric("Average quiz score", analytics["average_quiz_score"])
        st.metric("Learning interactions", analytics["learning_interaction_count"])
        topic_data = analytics["topic_performance"]
        if topic_data:
            try:
                import plotly.express as px

                chart_data = [item for item in topic_data if item["average_score"] is not None]
                if chart_data:
                    st.plotly_chart(px.bar(chart_data, x="topic", y="average_score", title="Topic performance"))
            except ImportError:
                st.info("Plotly is not installed; numeric analytics remain available.")
        st.json(analytics)

    st.header("Feedback")
    queries_response = _request("GET", "/api/feedback/queries")
    if queries_response.status_code == 200:
        queries = queries_response.json().get("queries", [])
        if queries:
            labels = {item["query_id"]: item["question"] for item in queries}
            selected_query = st.selectbox("Tutor response", list(labels), format_func=lambda value: labels[value])
            rating_labels = {1: "Helpful", 2: "Not helpful", 3: "Incorrect", 4: "Too difficult", 5: "Too simple"}
            rating = st.selectbox("Feedback category", list(rating_labels), format_func=lambda value: rating_labels[value])
            comments = st.text_area("Optional comments")
            if st.button("Submit feedback"):
                response = _request("POST", "/api/feedback", json={"query_id": selected_query, "rating": rating, "comments": comments})
                if response.status_code == 201:
                    st.success("Feedback submitted.")
                else:
                    st.error(response.json().get("error", "Feedback submission failed"))


st.set_page_config(page_title="LearnMate", page_icon="L")
st.title("LearnMate")
st.write("Student authentication")
st.caption(f"Backend: {API_URL}")
st.session_state.setdefault("session_id", None)

if st.session_state.session_id:
    _show_authenticated_state()
else:
    _show_auth_forms()

if st.button("Check Flask API health"):
    try:
        response = _request("GET", "/api/health")
        response.raise_for_status()
        payload = response.json()
        st.success(f"Flask API is reachable: {payload.get('status')}")
        st.json(payload)
    except requests.RequestException as exc:
        st.error(f"Flask API health check failed: {exc}")