

import pandas as pd
import numpy as np
from scipy.stats import skew, kurtosis
import os
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import RobustScaler, OneHotEncoder
from sklearn.preprocessing import LabelEncoder
from sklearn.compose import ColumnTransformer
from matplotlib import pyplot as plt
import seaborn as sns
from feature_engine.outliers import Winsorizer
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score
from sklearn.metrics import confusion_matrix, roc_curve, roc_auc_score
from sklearn.metrics import precision_score, recall_score, f1_score
from sklearn.model_selection import learning_curve
import joblib

# MySQL Database connection
from sqlalchemy import create_engine

downtime = pd.read_csv(r"D:\Project (Machine Downtime)\Data Set\Machine Downtime.csv")

# Creating engine which connect to MySQL
user = 'root' # user name
pw = 'priyanka' # password
db = 'downtime_db' # database

# creating engine to connect database
engine = create_engine(f"mysql+pymysql://{user}:{pw}@localhost/{db}")

# dumping data into database 
downtime.to_sql('machinedowntime', con = engine, if_exists = 'replace', chunksize = 1000, index = False)

# loading data from database
sql = 'select * from machinedowntime'

df = pd.read_sql_query(sql, con = engine)

df.head()
df.tail()
df.shape
df.info()
df.columns

df.describe()

# Drop the categorical columns 
column_to_drop = ['Date', 'Machine_ID', 'Assembly_Line_No']   ## as in classification models we dont include date columns
df.drop(column_to_drop, axis=1, inplace=True)

print(df)


# EDA of the dataset of 1st, 2nd, 3rd, 4rth business moments:
# Calculate moments for numerical columns
numerical_cols = df.select_dtypes(include=['float64', 'int64']).columns
moments = {}
for col in numerical_cols:
    moments[col] = {'Mean': df[col].mean(),
                    'Variance': df[col].var(),
                    'Skewness': df[col].skew(),
                    'Kurtosis': df[col].kurt()
                    }
    
# print results for each column separately
for col, stats in moments.items():
    print(f"Stats for column '{col}':")
    for stat, value in stats.items():
        print(f"{stat}: {value}")
    print() 


# Auto EDA 
import sweetviz as sv
s = sv.analyze(downtime)
s.show_html()

#splitting the data into input and output variables
X = pd.DataFrame(df.iloc[:,:-1])
Y = pd.DataFrame(df.iloc[:,-1:])
X
Y
###################### Data Cleaning #######################
# Identifying duplicate records
duplicate = df.duplicated() #returns boolean series denoting duplicate rows.
duplicate                   #no duplicates found

# check for missing values
missing_values = df.isnull().sum()
missing_values                    #missing values observed

#Numeric Features
numeric_features = X.select_dtypes(exclude = ['object']).columns
print(numeric_features)

#Imputation to handle missing values
#Robustscalar, beacuse outliers are present in the data
num_pipeline = Pipeline([('impute', SimpleImputer(strategy='median')), ('scale', RobustScaler())])
num_pipeline


#Using ColumnTransformer to transform the columns of an array or pandas Dataframe
#This estimator allows different columns or column sunsets of the input to be
#transformed separately and the features generated by each transformer will
#be concatenated to form a single feature space.
preprocess_pipeline = ColumnTransformer([('numerical', num_pipeline, numeric_features)],
                                        remainder = 'passthrough')
preprocess_pipeline

# pass the raw data through the pipeline
process = preprocess_pipeline.fit(X)

#save the model using joblib
joblib.dump(process, 'preprocess')

import os
os.getcwd()

## cleaned and preprocessed data
clean_data = pd.DataFrame(process.transform(X), columns = process.get_feature_names_out())
clean_data.describe()

# Heat map on cleaned data
# Calculate the correlation matrix
corr_matrix = clean_data.corr()

# Plot the heatmap
plt.figure(figsize=(12, 10))
sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', fmt=".2f", annot_kws={"size": 10})
plt.title('Correlation Heatmap of Cleaned Data', fontsize=16)
plt.tight_layout()
plt.show()

#outlier detection
data = ['numerical__Hydraulic_Pressure(bar)',
        'numerical__Coolant_Pressure(bar)',
        'numerical__Air_System_Pressure(bar)', 'numerical__Coolant_Temperature',
        'numerical__Hydraulic_Oil_Temperature(°C)',
        'numerical__Spindle_Bearing_Temperature(°C)',
        'numerical__Spindle_Vibration(µm)', 'numerical__Tool_Vibration(µm)',
        'numerical__Spindle_Speed(RPM)', 'numerical__Voltage(volts)',
        'numerical__Torque(Nm)', 'numerical__Cutting(kN)']


#Boxplot Before Outlier Treatment
plt.figure(figsize=(5, 4))
clean_data[data].boxplot()
plt.title('Boxplot Of Machine Downtime')
plt.xticks(rotation = 45, ha='right')
plt.xlabel('Columns')
plt.ylabel('Values')
plt.show()

# Scatter plot for each column to detect outliers
for column in data:
    plt.figure(figsize=(5, 4))
    plt.scatter(clean_data[column], clean_data[column], c='blue', label='Data')
    
    # Identify outliers and change their color to red
    outliers = clean_data[column].loc[clean_data[column] > clean_data[column].mean() + 2 * clean_data[column].std()]
    plt.scatter(outliers, outliers, c='red', label='Outliers')
    
    plt.xlabel(column)
    plt.ylabel(column)
    plt.title(f'Scatter Plot - {column} (Outlier Detection)')
    plt.legend()
    plt.show()
    
 
# Count the occurrences of machine failure
failure_counts = df['Downtime'].value_counts()

# Plot a pie chart
plt.figure(figsize=(5, 4))
plt.pie(failure_counts, labels=failure_counts.index, autopct='%1.1f%%', startangle=90)
plt.title('Machine Failure Occurrences')
plt.axis('equal')
plt.show()



#Encoding Y
label_encoder = LabelEncoder()
Y_encoded = label_encoder.fit_transform(Y)

############################################### Model Building #########################################


X_train , X_test , Y_train , Y_test = train_test_split(clean_data,Y_encoded, test_size=0.3 ,random_state=42)

X_test.to_csv("X_test.csv", index=False)


#################################### Decision Tree #####################################################

# Define the parameter grid for Decision Tree

param_grid_dt = {
    'criterion': ['gini', 'entropy'], # specifies the function to measure the quality of a split
    'max_depth': [2, 3, 4],       # specifies the maximum depth of the decision tree 
    'min_samples_split': [10, 15, 20],  # specifies the minimum number of samples required to split an internal node
    'min_samples_leaf': [10, 15, 20],   # specifies the minimum number of samples required to be at a leaf node.
    'max_features': [None]  # specifies the number of features to consider when looking for best split.
}


# Create the Decision Tree classifier
dt_model = DecisionTreeClassifier(random_state=42)

# Perform GridSearchCV for hyperparameter tuning
grid_search_dt = GridSearchCV(dt_model, param_grid_dt, cv=5, n_jobs=-1)
grid_search_dt.fit(X_train, Y_train)

# Get the best model from GridSearchCV
best_dt = grid_search_dt.best_estimator_

# Fit the best model on the training data
best_dt.fit(X_train, Y_train)

# Calculate training accuracy
train_dt_Y_pred = best_dt.predict(X_train)
train_dt_accuracy = accuracy_score(Y_train, train_dt_Y_pred)

# Print training accuracy
print("Training Accuracy:", train_dt_accuracy) # Training Accuracy: 0.944

# Make predictions on the test data
dt_Y_pred = best_dt.predict(X_test)

# Calculate testing accuracy
dt_accuracy = accuracy_score(Y_test, dt_Y_pred)

# Print testing accuracy
print("Testing Accuracy:", dt_accuracy) # Testing Accuracy: 0.942


# Saving the best model using joblib
joblib.dump(best_dt, 'decision_tree_model')



#################### Evaluation Metrics #############################

# Confusion Matrix
conf_matrix = confusion_matrix(Y_test, dt_Y_pred)
print("Confusion Matrix:")
print(conf_matrix)

# Plot Confusion Matrix
plt.figure(figsize=(5, 4))
sns.heatmap(conf_matrix, annot=True, fmt="d", cmap="Blues")
plt.title("Confusion Matrix")
plt.xlabel("Predicted Labels")
plt.ylabel("True Labels")
plt.show()


# Calculate Precision
precision = precision_score(Y_test, dt_Y_pred)
print("Precision:", precision)  # Precision: 0.945

# Calculate Recall
recall = recall_score(Y_test, dt_Y_pred)
print("Recall:", recall)  # Recall: 0.943

# Calculate F1-Score
f1 = f1_score(Y_test, dt_Y_pred)
print("F1-Score:", f1)  # F1-Score: 0.944


# ROC AUC score
roc_auc_best = roc_auc_score(Y_test, best_dt.predict_proba(X_test)[:, 1], average='weighted')
print("ROC AUC Score (after tuning):", roc_auc_best)  ## ROC AUC Score (after tuning): 0.961


def plot_learning_curve(estimator, title, X, y, cv=None, n_jobs=None, train_sizes=np.linspace(0.1, 1.0, 5)):
    plt.figure()
    plt.title(title)
    plt.xlabel("Training examples")
    plt.ylabel("Score")
    
    train_sizes, train_scores, test_scores = learning_curve(
        estimator, X, y, cv=cv, n_jobs=n_jobs, train_sizes=train_sizes, scoring='accuracy'
    )
    
    train_scores_mean = np.mean(train_scores, axis=1)
    train_scores_std = np.std(train_scores, axis=1)
    test_scores_mean = np.mean(test_scores, axis=1)
    test_scores_std = np.std(test_scores, axis=1)
    
    plt.grid()
    
    plt.fill_between(train_sizes, train_scores_mean - train_scores_std,
                     train_scores_mean + train_scores_std, alpha=0.1,
                     color="r")
    plt.fill_between(train_sizes, test_scores_mean - test_scores_std,
                     test_scores_mean + test_scores_std, alpha=0.1, color="g")
    plt.plot(train_sizes, train_scores_mean, 'o-', color="r",
             label="Training score")
    plt.plot(train_sizes, test_scores_mean, 'o-', color="g",
             label="Testing score")
    
    plt.legend(loc="best")
    return plt


plot_learning_curve(best_dt, "Learning Curves (Decision Tree)", clean_data, Y_encoded, cv=5, n_jobs=-1)
plt.show()



