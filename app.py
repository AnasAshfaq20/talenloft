import streamlit as st
from sqlalchemy import create_engine, or_
from sqlalchemy.orm import sessionmaker
from schema import (
    Job, Candidate, Skill, LocationType,
    SkillLevel, CareerPreference, Availability
)

# Database connection
DATABASE_URL = st.secrets["DATABASE_URL"]
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()


# Matching algorithm (needs to be imported or defined here)
def calculate_matching_score(job, candidate):
    # Skill Matching (40%)
    job_skills = {(s.skill_group, s.skill_level) for s in job.skills}
    candidate_skills = {(s.skill_group, s.skill_level) for s in candidate.skills}
    full_matches = len(job_skills & candidate_skills)
    partial_matches = len({sg for sg, _ in job_skills} & {sg for sg, _ in candidate_skills}) - full_matches
    skill_score = (full_matches * 10 + partial_matches * 5) * 0.4

    # Experience (30%) - Add safe type checking
    try:
        candidate_exp = int(candidate.total_experience) if candidate.total_experience is not None else 0
        job_exp = int(job.required_experience) if job.required_experience is not None else 0
        exp_score = 10 * 0.3 if candidate_exp >= job_exp else -5 * 0.3
    except (TypeError, ValueError):
        exp_score = -5 * 0.3  # Default to penalty if experience is invalid

    # Career Preference (20%)
    career_score = 10 * 0.2 if job.career_preference == candidate.career_preference else -10 * 0.2

    # Location & Salary (10%)
    location_score = 10 if job.location_type == candidate.preferred_location else 5 if "Hybrid" in [job.location_type, candidate.preferred_location] else 0
    salary_overlap = (candidate.expected_salary_min <= job.salary_max) and (candidate.expected_salary_max >= job.salary_min)
    salary_score = 10 if salary_overlap else 5 if (candidate.expected_salary_min <= job.salary_max + 20000) else 0
    location_salary_score = (location_score + salary_score) * 0.05

    return skill_score + exp_score + career_score + location_salary_score


# Streamlit App
st.title("talentloft Matching Portal")

# Sidebar navigation
menu = st.sidebar.selectbox("Menu", [
    "For Candidates ➡️", 
    "For Employers 🏢",
    "Find Matches 🔍"
])

# Helper function to get all skills
def get_all_skills():
    return session.query(Skill).all()

 # Add validation helpers
def validate_salary(min_salary, max_salary):
    if not (isinstance(min_salary, int) and isinstance(max_salary, int)):
        raise ValueError("Salaries must be integers")
    if min_salary > max_salary:
        raise ValueError("Minimum salary cannot be greater than maximum salary")
    return min_salary, max_salary

def validate_experience(exp):
    try:
        exp = int(exp)
        if exp < 0:
            raise ValueError("Experience cannot be negative")
        return exp
    except (TypeError, ValueError):
        raise ValueError("Experience must be a positive integer")

# Add this helper function after the other helper functions
def format_skills(skills):
    return ", ".join([f"{s.skill_group} ({s.skill_level.name})" for s in skills])

# Candidate Section
if menu == "For Candidates ➡️":
    st.header("Candidate Portal")
    
    with st.expander("➕ Create New Candidate Profile"):
        # Inside the candidate form submission:
        with st.form("candidate_form"):
            username = st.text_input("Username (Anonymous)")
            total_experience = st.number_input("Total Experience (years)", 0, 40, 0)
            pref_location_str = st.selectbox("Preferred Location", [lt.value for lt in LocationType])
            salary_min = st.number_input("Minimum Expected Salary ($)", 30000, 200000, 60000)
            salary_max = st.number_input("Maximum Expected Salary ($)", 30000, 200000, 100000)
            career_pref_str = st.selectbox("Career Preference", [cp.value for cp in CareerPreference])
        
            # Skill selection
            all_skills = get_all_skills()
            selected_skills = st.multiselect(
                "Your Skills", 
                [f"{s.skill_group} ({s.skill_level.name})" for s in all_skills]
            )
            
            submitted = st.form_submit_button("Create Profile")
        
        if submitted:
            try:
                # Validate inputs
                total_experience = validate_experience(total_experience)
                salary_min, salary_max = validate_salary(
                    int(salary_min), int(salary_max)
                )
                
                # Convert enums
                pref_location = LocationType(pref_location_str)
                career_pref = CareerPreference(career_pref_str)
                
                new_candidate = Candidate(
                    username=username.strip(),
                    total_experience=total_experience,
                    preferred_location=pref_location,
                    expected_salary_min=salary_min,
                    expected_salary_max=salary_max,
                    career_preference=career_pref
                )
                
                # Validate and add skills
                if not selected_skills:
                    raise ValueError("Please select at least one skill")
                    
                for skill_str in selected_skills:
                    skill_name, level_str = skill_str.split(" (")
                    level_str = level_str[:-1]
                    level = SkillLevel[level_str.upper()]
                    
                    skill = session.query(Skill).filter(
                        Skill.skill_group == skill_name,
                        Skill.skill_level == level
                    ).first()
                    
                    if not skill:
                        raise ValueError(f"Invalid skill: {skill_str}")
                        
                    new_candidate.skills.append(skill)
                
                session.add(new_candidate)
                session.commit()
                st.success("Profile created successfully!")
                
                # Show immediate matches
                st.subheader("Your Top Job Matches")
                jobs = session.query(Job).all()
                matches = []
                for job in jobs:
                    score = calculate_matching_score(job, new_candidate)
                    matches.append((job, score))
                
                matches.sort(key=lambda x: x[1], reverse=True)
                
                for job, score in matches[:5]:
                    st.write(f"**{job.title}**")
                    st.write(f"Skills: {format_skills(job.skills)}")
                    st.write(f"Score: {score:.1f} | 💰 {job.salary_min}-{job.salary_max}$")
                    st.write(f"📍 {job.location_type} | 📅 {job.availability}")
                    st.write("---")
            
            except ValueError as e:
                st.error(f"Invalid input: {str(e)}")
            except Exception as e:
                st.error(f"Error creating profile: {str(e)}")
                session.rollback()

# Employer Section
elif menu == "For Employers 🏢":
    st.header("Employer Portal")
    
    with st.expander("📝 Post New Job"):
        with st.form("job_form"):
            title = st.text_input("Job Title")
            req_exp = st.number_input("Required Experience (years)", 0, 10, 3)
            location_str = st.selectbox("Location Type", 
                                      [lt.value for lt in LocationType])
            salary_min = st.number_input("Minimum Salary ($)", 30000, 200000, 80000)
            salary_max = st.number_input("Maximum Salary ($)", 30000, 200000, 120000)
            availability_str = st.selectbox("Availability Required",
                                          [a.value for a in Availability])
            career_pref_str = st.selectbox("Career Preference",
                                         [cp.value for cp in CareerPreference])
            
            # Skill requirements
            all_skills = get_all_skills()
            required_skills = st.multiselect("Required Skills", 
                                           [f"{s.skill_group} ({s.skill_level.name})" 
                                            for s in all_skills],
                                           format_func=lambda x: x)
            
            submitted = st.form_submit_button("Post Job")
            
            if submitted:
                try:
                    # Validate inputs
                    req_exp = validate_experience(req_exp)
                    salary_min, salary_max = validate_salary(
                        int(salary_min), int(salary_max)
                    )
                    
                    # Convert enums
                    location_type = LocationType(location_str)
                    availability = Availability(availability_str)
                    career_pref = CareerPreference(career_pref_str)
                    
                    new_job = Job(
                        title=title.strip(),
                        required_experience=req_exp,
                        location_type=location_type,
                        salary_min=salary_min,
                        salary_max=salary_max,
                        availability=availability,
                        career_preference=career_pref
                    )
                    
                    # Validate and add skills
                    if not required_skills:
                        raise ValueError("Please select at least one required skill")
                        
                    for skill_str in required_skills:
                        skill_name, level_str = skill_str.split(" (")
                        level = SkillLevel[level_str[:-1].upper()]
                        skill = session.query(Skill).filter(
                            Skill.skill_group == skill_name,
                            Skill.skill_level == level
                        ).first()
                        
                        if not skill:
                            raise ValueError(f"Invalid skill: {skill_str}")
                            
                        new_job.skills.append(skill)
                    
                    session.add(new_job)
                    session.commit()
                    st.success("Job posted successfully!")
                    
                    # Show immediate matches
                    st.subheader("Top Candidate Matches")
                    candidates = session.query(Candidate).all()
                    matches = []
                    for candidate in candidates:
                        score = calculate_matching_score(new_job, candidate)
                        matches.append((candidate, score))
                    
                    matches.sort(key=lambda x: x[1], reverse=True)
                    
                    for candidate, score in matches[:5]:
                        st.write(f"**{candidate.username}**")
                        st.write(f"Skills: {format_skills(candidate.skills)}")
                        st.write(f"Score: {score:.1f} | 💰 {candidate.expected_salary_min}-{candidate.expected_salary_max}$")
                        st.write(f"📍 {candidate.preferred_location} | 🎯 {candidate.career_preference}")
                        st.write("---")
                
                except ValueError as e:
                    st.error(f"Invalid input: {str(e)}")
                except Exception as e:
                    st.error(f"Error posting job: {str(e)}")
                    session.rollback()
