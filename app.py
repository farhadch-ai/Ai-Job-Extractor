import os
import streamlit as st
import pandas as pd

from extractor import extract_jobs
from cleaner import clean_jobs
from storage import save_jobs


CSV_FILE = "jobs_clean.csv"


# ==================================================
# SESSION STATE
# ==================================================

if "job_text" not in st.session_state:
    st.session_state.job_text = ""

if "clear_text" not in st.session_state:
    st.session_state.clear_text = False


# Clear text BEFORE creating the text widget
if st.session_state.clear_text:
    st.session_state.job_text = ""
    st.session_state.clear_text = False


# ==================================================
# TITLE
# ==================================================

st.title("Freelance Job Extractor")


# ==================================================
# INPUT
# ==================================================

st.subheader("Add Jobs")


job_text = st.text_area(
    "Paste the job posts here:",
    key="job_text"
)


# ==================================================
# FILE UPLOAD
# ==================================================

uploaded_file = st.file_uploader(
    "Or upload a text file:",
    type=["txt"]
)


if uploaded_file:

    job_text = uploaded_file.read().decode("utf-8")

    st.info(
        "Text file uploaded successfully."
    )


# ==================================================
# EXTRACT JOBS
# ==================================================

if st.button("Extract Jobs"):

    if not job_text.strip():

        st.warning(
            "Please paste or upload some job text."
        )

    else:

        try:

            # --------------------------------------
            # AI extraction
            # --------------------------------------

            with st.spinner("Extracting jobs..."):

                result = extract_jobs(job_text)


            # --------------------------------------
            # Get jobs
            # --------------------------------------

            jobs = result["jobs"]


            # --------------------------------------
            # Token usage
            # --------------------------------------

            input_tokens = result["input_tokens"]
            output_tokens = result["output_tokens"]
            total_tokens = result["total_tokens"]


            # --------------------------------------
            # Clean jobs BEFORE display
            # --------------------------------------

            cleaned_jobs = clean_jobs(jobs)


            # --------------------------------------
            # No jobs found
            # --------------------------------------

            if not cleaned_jobs:

                st.warning(
                    "No valid jobs were found."
                )


            else:

                # ==================================
                # TOKEN USAGE
                # ==================================

                st.subheader("Token Usage")


                col1, col2, col3 = st.columns(3)


                col1.metric(
                    "Input Tokens",
                    input_tokens
                )


                col2.metric(
                    "Output Tokens",
                    output_tokens
                )


                col3.metric(
                    "Total Tokens",
                    total_tokens
                )


                # ==================================
                # DISPLAY JOBS
                # ==================================

                st.subheader(
                    f"Extracted Jobs: {len(cleaned_jobs)}"
                )


                for number, job in enumerate(
                    cleaned_jobs,
                    start=1
                ):

                    st.markdown(
                        f"### Job {number}"
                    )


                    st.write(
                        "**Title:**",
                        job.title
                    )


                    st.write(
                        "**Project Type:**",
                        job.project_type
                    )


                    st.write(
                        "**Skills:**",
                        ", ".join(job.skills)
                    )


                    st.write(
                        "**Budget:**",
                        job.budget_min,
                        "-",
                        job.budget_max
                    )


                    st.write(
                        "**Budget Type:**",
                        job.budget_type
                    )


                    st.write(
                        "**Negotiable:**",
                        job.budget_negotiable
                    )


                    st.write(
                        "**Client Problem:**",
                        job.client_problem
                    )


                    st.write(
                        "**Experience:**",
                        job.experience_level
                    )


                    st.write(
                        "**Posted:**",
                        job.posted_ago
                    )


                    st.divider()


                # ==================================
                # SAVE JOBS
                # ==================================

                try:

                    save_jobs(cleaned_jobs)

                    st.success(
                        "Jobs saved to SQLite and CSV."
                    )

                    # Tell the next Streamlit run
                    # to clear the text box.
                    st.session_state.clear_text = True

                    st.rerun()


                except Exception as e:

                    st.error(
                        f"Could not save jobs: {e}"
                    )


        except Exception as e:

            st.error(
                f"Extraction failed: {e}"
            )


# ==================================================
# DOWNLOAD CSV
# ==================================================

st.subheader("Download Jobs")


if os.path.exists(CSV_FILE):

    try:

        csv_df = pd.read_csv(CSV_FILE)


        if csv_df.empty:

            st.error(
                "The CSV file exists but contains no jobs."
            )


        else:

            csv_data = csv_df.to_csv(
                index=False
            ).encode("utf-8")


            st.download_button(
                label="Download CSV",
                data=csv_data,
                file_name="jobs_clean.csv",
                mime="text/csv"
            )


    except Exception as e:

        st.error(
            f"Could not read the CSV file: {e}"
        )


else:

    st.error(
        "CSV file does not exist yet. "
        "Extract and save some jobs first."
    )


# ==================================================
# SEARCH JOBS
# ==================================================

st.subheader("Search Jobs")


search_text = st.text_input(
    "Search by title, skills, project type, "
    "or client problem:"
)


if search_text.strip():

    if not os.path.exists(CSV_FILE):

        st.error(
            "No jobs database is available yet. "
            "Extract and save some jobs first."
        )


    else:

        try:

            search_df = pd.read_csv(CSV_FILE)


            if search_df.empty:

                st.error(
                    "The jobs database is empty."
                )


            else:

                search_columns = [
                    "title",
                    "skills",
                    "project_type",
                    "client_problem",
                    "experience_level"
                ]


                # Only search columns that exist
                search_columns = [
                    column
                    for column in search_columns
                    if column in search_df.columns
                ]


                if not search_columns:

                    st.error(
                        "The CSV does not contain "
                        "searchable job fields."
                    )


                else:

                    # Start with no matches
                    mask = pd.Series(
                        False,
                        index=search_df.index
                    )


                    # Search every selected column
                    for column in search_columns:

                        mask = mask | (
                            search_df[column]
                            .fillna("")
                            .astype(str)
                            .str.contains(
                                search_text,
                                case=False,
                                na=False,
                                regex=False
                            )
                        )


                    results = search_df[mask]


                    # --------------------------------
                    # SEARCH RESULTS
                    # --------------------------------

                    if results.empty:

                        st.warning(
                            f'No jobs found for "{search_text}".'
                        )


                    else:

                        st.success(
                            f"{len(results)} job(s) found."
                        )


                        st.dataframe(
                            results,
                            use_container_width=True
                        )


        except Exception as e:

            st.error(
                f"Could not search the jobs: {e}"
            )