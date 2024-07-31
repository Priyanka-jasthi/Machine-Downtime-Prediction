import pandas as pd
import streamlit as st
from sqlalchemy import create_engine
import pickle, joblib

model = joblib.load('decision_tree_model')
impute = joblib.load('preprocess')

def predict_Downtime(data, user, pw, db):
    engine = create_engine(f"mysql+pymysql://{user}:{pw}@localhost/{db}")
    
    data = data.drop(columns=['Date'])
    
    clean_data = pd.DataFrame(impute.transform(data), columns=impute.get_feature_names_out())

    prediction = pd.DataFrame(model.predict(clean_data), columns=['prediction'])
    
    final = pd.concat([prediction, data], axis=1)
    final.to_sql('downtime_predictions', con=engine, if_exists='replace', chunksize=1000, index=False)

    return final

def main():
    st.title("Machine Downtime Prediction")
    st.sidebar.title("Machine Downtime Prediction")

    html_temp = """
    <div style="background-color:tomato;padding:10px">
    <h2 style="color:white;text-align:center;">Machine Downtime</h2>
    </div>
    """
    st.markdown(html_temp, unsafe_allow_html=True)
    st.text("")
    
    uploadedFile = st.sidebar.file_uploader("Choose a file", type=['csv', 'xlsx'], accept_multiple_files=False, key="fileUploader")
    if uploadedFile is not None:
        try:
            data = pd.read_csv(uploadedFile)
        except:
            try:
                data = pd.read_excel(uploadedFile)
            except:
                data = pd.DataFrame(uploadedFile)
    else:
        st.sidebar.warning("You need to upload a csv or excel file.")
    
    html_temp = """
    <div style="background-color:tomato;padding:10px">
    <p style="color:white;text-align:center;">Add Database Credentials</p>
    </div>
    """
    st.sidebar.markdown(html_temp, unsafe_allow_html=True)
    
    user = st.sidebar.text_input("User", "Type Here")
    pw = st.sidebar.text_input("Password", "Type Here", type="password")
    db = st.sidebar.text_input("Database", "Type Here")
    
    result = ""
    
    if st.button("Predict"):
        result = predict_Downtime(data, user, pw, db)
        st.table(result)
        
        import seaborn as sns
        cm = sns.light_palette("blue", as_cmap=True)
        st.table(result.style.background_gradient(cmap=cm).set_precision(2))

if __name__ == '__main__':
    main()


