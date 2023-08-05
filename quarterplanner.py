import streamlit as st
from streamlit.connections import ExperimentalBaseConnection
import re
import pandas as pd
from explorecourses import *
import streamlit_analytics

streamlit_analytics.start_tracking()
st.set_page_config(page_title = "Quarter Planner", page_icon = "🍔")


class ExploreCoursesConnection(ExperimentalBaseConnection["course_connection.CourseConnection"]):
    def _connect(self):
        connectObject = CourseConnection()
        return connectObject
    
    def cursor(self):
        connectObject = CourseConnection()
        return connectObject
    
    #query method to retrieve data
    #cache makes it so lightning fast; cache each department permanently. should never reach 1GB limit
    @st.cache_data(persist="disk", show_spinner="Loading departments...")
    #make sure to hash dept and year so things change
    def query(_self, _cursor, dept, year):
        print("department is")
        print(dept)
        search_results = _cursor.get_courses_by_department(dept, year=year)
        return search_results
    

conn = st.experimental_connection(name="Explore", type=ExploreCoursesConnection)
cursor = conn.cursor()


#remove blank space at top
st.markdown(
    """
        <style>
            .appview-container .main .block-container {{
                padding-top: {padding_top}rem;
                padding-bottom: {padding_bottom}rem;
                }}

        </style>""".format(
        padding_top=0, padding_bottom=.25
    ),
    unsafe_allow_html=True,
)

#split input into classes
def separate_classes(input_text):
    residual = ''
    # Split input text based on comma separator
    input_text = input_text.replace("; ", ",")  #immutable string
    input_text = input_text.replace(' OR ', ',')  
    input_text = input_text.replace('†', '')  

    input_text = input_text.replace(', ', ',')  #take out spaces for later split with only ,

    input_text = re.sub(r'\([^)]*\)', '', input_text)
    classes = input_text.split(",")
    # Initialize an empty array to store the separated classes
    separated_classes = []
    # Regular expression pattern to split based on alphabets to numbers transition
    pattern = re.compile(r'([a-zA-Z&\s]+)(\d*.*\d*)')
    # Iterate over each class and split it into department and code
    for class_item in classes:
        match = pattern.match(class_item)
        if match:
            department = match.group(1).strip()
            residual = department
            code = match.group(2).strip()
            separated_classes.append((department, code))
        else: #if no department, use last department - easy copy paste from program sheet
            department = residual
            code = class_item.strip()
            separated_classes.append((department, code))
    return separated_classes


@st.cache_data(persist="disk")
def page_setup():
    st.title('🍔 Stanford Quarter Planner')
    st.header("Enter a comma-separated list of courses you want to take.")
    st.markdown("Tip: When entering courses from the same department, only include the department\
                on the first course, e.g. CS 229, 234, EE 263, 364A.\
                The input text is also stripped of semicolons, 'or', parentheticals, etc for further\
                ease of copy-pasting from program sheets.")
    st.write("Relevant links: [CS AI Program Sheet](https://cs.stanford.edu/degrees/ug/ProgramSheets/CS_AI_2223PS.pdf), \
            [MSCS AI Program Sheet](https://cs.stanford.edu/degrees/mscs/programsheets/22-23/MSCS-2023-AI.pdf), \
            [Math Major Program Sheet](https://drive.google.com/file/d/12pAlP0mjBcU0Atflgn6pg5V1pRcif5kZ/view), \
            [Aero/Astro Program Sheet](https://drive.google.com/file/d/1d_DNjzOMeAffM_wFPBwa24gu7urgJGKH/view), \
            [Other UGHB Program Sheets](https://ughb.stanford.edu/plans-program-sheets/program-sheets/program-sheets/program-sheets/program-sheets/program-sheets), \
            [ExploreCourses main site](explorecourses.stanford.edu)")





page_setup()


#get input, make uppercase and format
with st.form(key='my_form'):
    #not sure why 2022-2023 not working, maybe API change
    year = st.selectbox('Pick year', ('2023-2024', '2022-2023'), index=0, help="Majority of courses\
                        are already published on ExploreCourses for 2023-2024")
    #year = "2023-2024"
    #st.write("Year: 2023-2024")
    #use 'value=example_input' below if wanted
    user_input = st.text_input(label="Classes", placeholder="Your classes", label_visibility="collapsed").upper()
    submit_button = st.form_submit_button(label='Submit')
user_input_separated = separate_classes(user_input)


#session state so no table shows until interacted with
if submit_button:
    if "submitted" not in st.session_state:
        st.session_state.submitted = True

if "submitted" in st.session_state:
    if st.session_state.submitted:
        submit_button = True


#grab courses using search, choose right ones
#reduced queries; only one for each dept
#marks unvalidated courses
#can't make function; messes with df
user_courses = []
dept_dict = {}
first_unvalid = False
unvalidated = ""
for stanfordClass in user_input_separated:
    current_unvalid = True
    if stanfordClass[0] not in dept_dict:
        search_results = conn.query(cursor, stanfordClass[0], year)  #function to save dept courses
        dept_dict.update({stanfordClass[0]: search_results})
    #linear search fine for small; cs has 350 courses
    for course in dept_dict.get(stanfordClass[0])[:]:   #skip 20 for low level courses; can't do for aero
        if course.code == stanfordClass[1]:
            user_courses.append(course)
            current_unvalid = False
            break
    if current_unvalid and not first_unvalid:
        unvalidated = str(stanfordClass[0]) + str(stanfordClass[1])
        first_unvalid = True
    elif current_unvalid:
        unvalidated += ", " + stanfordClass[0] + stanfordClass[1]


#show which courses are found and which are not
if submit_button:
    if(len(user_courses) == 0):
        st.warning("None of your entered courses could be found for " + year + "!", icon="⚠️")
        st.stop()
with st.expander("Courses found and not found for " + year):
    if submit_button:        
        validated = user_courses[0].subject + user_courses[0].code
        for course in user_courses[1:]:
            validated += ", " + course.subject + course.code
        st.success("Found: " + validated + ".")
        if unvalidated != "":
            st.error("Not found: " + unvalidated + ".  \nUnvalidated courses\
                    are most likely not offered this year; in the case of higher level classes they may have letter \
                    suffixes not included on program sheet e.g. listed as CS272, course is CS272B.")


#initialize dataframe
headers = ['Autumn', 'Winter', 'Spring', 'All', 'Autumn/Winter', 'Autumn/Spring', 'Winter/Spring']
header_count = [0,0,0,0,0,0,0]
num_rows = 5
df = pd.DataFrame(columns=headers, index=range(num_rows))
df = df.fillna('')

options = {"AUT", "WIN", "SPR"} #bad code design
combo1 = {"AUT", "WIN"}
combo2 = {"AUT", "SPR"}
combo3 = {"WIN", "SPR"}

#user interface
toggle = st.checkbox("Toggle course descriptions")
if toggle:
    wordsToShow = 15
else:
    wordsToShow = 1

#add to table based on quarter, expand table as needed
if submit_button:
    for course in user_courses:
        location = 10 #skip this class if not offered/only in summer. maybe should show?
        quarters = course.attributes
        quarter_str = ''
        for q in quarters:
            quarter_str += str(q).split("::")[1]        

        if quarter_str == 'AUT':
            location = 0
        elif quarter_str == 'WIN':
            location = 1
        elif quarter_str == 'SPR':
            location = 2
        elif all([x in quarter_str for x in options]):
            location = 3
        elif all([x in quarter_str for x in combo1]):
            location = 4
        elif all([x in quarter_str for x in combo2]):
            location = 5
        elif all([x in quarter_str for x in combo3]):
            location = 6
        
        if location == 10:
            continue
        
        df.iloc[header_count[location], location] = ' '.join(str(course).split()[:wordsToShow]) #course and first (5-1) words
        header_count[location] += 1
        if any(y in header_count for y in range(num_rows - 2, num_rows - 1)): #expand table as needed, must be 2
            new_row = pd.DataFrame(index=[len(df)])
            df = pd.concat([df, new_row])
            df = df.fillna('')
            num_rows += 1

        if num_rows > 13:
            df.iloc[10, 3] = "⚠️You are not graduating⚠️"


#display result dataframe; 2 options
st.table(df)
#st.dataframe(df, hide_index=True, width = 9999)


st.markdown("---")

col1, col2 = st.columns([1, 1])
with col1:
    st.write("Based on [explore-courses-api](https://github.com/jeremyephron/explore-courses-api) by \
        Jeremy Ephron.")
with col2:
    st.markdown("<div style='text-align: right;'><a href='https://github.com/joshua-bowden/quarterplanner' style='color: green;'>See Quarter Planner's source code</a></div>", unsafe_allow_html=True)


streamlit_analytics.stop_tracking()

         



