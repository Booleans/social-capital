import pandas as pd
from datetime import datetime as dt
from io import BytesIO
import boto3
from src.feature_engineering import *

def load_loan_data_from_local_machine(csv_files, columns, number_of_rows=None):
    '''
    Function to take a list of CSV files that contain the data on Lending Club's loans and 
    concatenate them into one dataframe. This function is to be used when the CSV files are stored
    on a local machine and are not being loaded from an AWS S3 bucket.

    Args:
        csv_files (list or tuple): List of CSV files that contain the data. Files should be stored in the /data
        folder. Below is a tuple of the names of the available files from Lending Club as of April 2019.
        ('LoanStats3a_securev1.csv', 'LoanStats3b_securev1.csv', 'LoanStats3c_securev1.csv', 'LoanStats3d_securev1.csv',
         'LoanStats_securev1_2016Q1.csv', 'LoanStats_securev1_2016Q2.csv', 'LoanStats_securev1_2016Q3.csv',
         'LoanStats_securev1_2016Q4.csv', 'LoanStats_securev1_2017Q1.csv', 'LoanStats_securev1_2017Q2.csv', 
         'LoanStats_securev1_2017Q3.csv', 'LoanStats_securev1_2017Q4.csv', 'LoanStats_securev1_2018Q1.csv',
         'LoanStats_securev1_2018Q2.csv', 'LoanStats_securev1_2018Q3.csv', 'LoanStats_securev1_2018Q4.csv')

        columns (list or tuple): List of column names that should be used in the dataframe. Certain columns should be
        excluded due to the fact they would not have been available at the time the loan was issued.
        The list of accetable columns is generated by the the file `columns.py` in the src folder.

        number_of_rows (int or None): The number of rows to load from each CSV file. This is used to load in smaller 
        amounts of data for testing purposes. By default, number_of_rows is None, which loads all data. 

    Returns:
        DataFrame: Returns a dataframe containing all loans contained within the list of CSV files. 
    '''
    loan_data = []
    for filename in csv_files:    
        data = pd.read_csv(f'data/{filename}', header=1, low_memory=False, na_values='n/a',
                           usecols=columns, nrows=number_of_rows) 
        loan_data.append(data)
    loans = pd.concat(loan_data)
    # Loan IDs are unique and we can access specific loans much faster by setting them as the index.
    #loans.set_index('id', inplace=True)
    return loans

def load_loan_data_from_s3(csv_files, columns, number_of_rows=None, bucket='loan-analysis-data'):
    '''
    Function to take a list of loan data CSV files that stored in an AWS S3 bucket and load and
    concatenate them into one dataframe.

    Args:
        csv_files (list or tuple): List of CSV files that contain the data. Below is a tuple of the names of the
        available files from Lending Club as of April 2019.
        ('LoanStats3a_securev1.csv', 'LoanStats3b_securev1.csv', 'LoanStats3c_securev1.csv', 'LoanStats3d_securev1.csv',
         'LoanStats_securev1_2016Q1.csv', 'LoanStats_securev1_2016Q2.csv', 'LoanStats_securev1_2016Q3.csv',
         'LoanStats_securev1_2016Q4.csv', 'LoanStats_securev1_2017Q1.csv', 'LoanStats_securev1_2017Q2.csv', 
         'LoanStats_securev1_2017Q3.csv', 'LoanStats_securev1_2017Q4.csv', 'LoanStats_securev1_2018Q1.csv',
         'LoanStats_securev1_2018Q2.csv', 'LoanStats_securev1_2018Q3.csv', 'LoanStats_securev1_2018Q4.csv')

        columns (list or tuple): List of column names that should be used in the dataframe. Certain columns should be
        excluded due to the fact they would not have been available at the time the loan was issued.
        The list of accetable columns is generated by the the file `columns.py` in the src folder and stored in 
        the variable columns_to_use.

        number_of_rows (int or None): The number of rows to load from each CSV file. This is used to load in smaller 
        amounts of data for testing purposes. By default, number_of_rows is None, which loads all data.

        bucket (string): Name of the S3 bucket the files are stored in. My bucket is called 'loan-analysis-data'.

    Returns:
        DataFrame: Returns a dataframe containing all loans contained within the list of CSV files.  
    '''
    loan_data = []
    for filename in csv_files:
        s3 = boto3.client('s3')
        obj = s3.get_object(Bucket=bucket, Key=filename)
        data = obj['Body'].read()
        f = BytesIO(data)
        data = pd.read_csv(f, header=1, low_memory=False, na_values='n/a',
                           usecols=columns, nrows=number_of_rows) 
        loan_data.append(data)
    loans = pd.concat(loan_data)
    # Loan IDs are unique and we can access specific loans much faster by setting them as the index.
    #loans.set_index('id', inplace=True)
    return loans

def drop_loans_not_complete(df):
    '''
    Drop loans that are still outstanding. If we want to analyze completed loans we need to only
    include loans with a status of 'Charged Off' or 'Fully Paid'.

    Args:
        df (dataframe): Dataframe of loans.

    Returns:
        DataFrame: Returns dataframe that only includes loans that are charged off or fully paid. 
    '''
    mask = df['loan_status'].isin(('Charged Off', 'Fully Paid'))
    return df.loc[mask, :]

def drop_loan_status(df):
    '''
    Drop loan status column for training. We don't know when a loan is issued whether it will end up fully paid
    or defaulted on.

    Args:
        df (dataframe): Dataframe of loans.

    Returns:
        DataFrame: Returns dataframe where the loan status column has been dropped.
    '''
    df = df.drop('loan_status', axis=1)
    return df

def drop_joint_applicant_loans(df):
    '''
    Drop loans that are issued to joint applicants instead of individuals. This loan type is relatively new and will
    be excluded for now.

    Args:
        df (dataframe): Dataframe of loans.

    Returns:
        DataFrame: Returns dataframe that only contains loans issued to individuals and not joint applicants.
    '''
    mask = df['application_type'].str.upper() == "INDIVIDUAL"
    return df.loc[mask, :]

def fix_rate_cols(df):
    '''
    Fix the data types of columns that are related to interest rates. They were read in as strings instead of floats due to
    the fact they contain the symbol for percent. For example, a loan with interest rate '16.37%'. As of April 2019 the
    two columns that need to be fixed are 'int_rate' and 'revol_util'. 

    Args:
        df (dataframe): Dataframe of loans.

    Returns:
        DataFrame: Returns dataframe where the interest rate columns that were incorrectly read in as strings
        have been converted to floats.
    '''
    # Columns that end with % were read in as strings instead of floats. We need to remove the % and change data types.
    rate_cols = ('int_rate', 'revol_util')
    for col in rate_cols:
        df[col] = df[col].str.rstrip('%').astype('float32')
    return df

def clean_loan_term_col(df):
    '''
    Convert the loan term column to an integer instead of a string. We convert "36 months" into 36 and "60 months" into 60.

    Args:
        df (dataframe): Dataframe of loans.

    Returns:
        DataFrame: Returns dataframe where the loan term column is now an int instead of a string. 
    '''
    df['term'] = [36 if row.strip() == '36 months' else 60 for row in df['term']]
    df['term'] = df['term'].astype('uint8')
    return df 

def only_include_36_month_loans(df):
    '''
    Exclude loans that aren't 36 months in duration. If investors want to include 60 month loans as well this function can be 
    abandoned.

    Args:
        df (dataframe): Dataframe of loans.

    Returns:
        DataFrame: Returns dataframe that includes only loans that are 36 months in duration. 
    '''
    mask = df['term'] == 36
    return df.loc[mask, :]

def clean_employment_length(df):
    '''
    Change the employment length column so that '<1 year' becomes 0 years. Then convert column from string to a float.

    Args:
        df (dataframe): Dataframe of loans.

    Returns:
        DataFrame: Returns dataframe where 'emp_length' column is now a float.

    Todo:
        Why a float and not an int?
    '''
    df['emp_length'] = [0 if row == '< 1 year' else row for row in df['emp_length']]
    df['emp_length'] = df['emp_length'].str.extract('(\d+)', expand=True).astype('float32')
    return df

def convert_date(col_date):
    '''
    The columns related to dates are read in as strings. This function is designed to convert a column to a datetime
    date type. These columns come in 2 formats and this function handles both.

    Args:
        df (dataframe): Dataframe column that you want to convert to a datetime dtype. 

    Returns:
        DataFrame: Returns column in datetime format. 
    '''
    if col_date[0].isdigit():
        # Need to pad the date string with a 0 if it's too short. 
        col_date = col_date.rjust(6, '0')
        return pd.to_datetime(col_date, format = '%y-%b')
    else:
        try:
            return pd.to_datetime(col_date, format = '%b-%y')
        except:
            return pd.to_datetime(col_date, format = '%b-%Y')

def fix_date_cols(df):
    '''
    Function relies on the previous function, convert_date, to fix columns that are supposed to be datetime dtypes.
    Columns fixed are loan issue date, earliest credit line, and last payment date.

    Args:
        df (dataframe): Dataframe of loans.

    Returns:
        DataFrame: Dataframe where the loan columns have been converted to the datetime dtype. 
    '''
    df.dropna(subset=['issue_d'], inplace=True)
    df['issue_d'] = df['issue_d'].map(convert_date)
    df['earliest_cr_line'] = df['earliest_cr_line'].map(convert_date)
    df.dropna(subset=['last_pymnt_d'], inplace = True)
    df['last_pymnt_d'] = df['last_pymnt_d'].map(convert_date)
    return df

def fill_nas(df, value=-99):
    '''
    Function to fill in missing values so that our tree models can handle the data.

    Args:
        df (dataframe): Dataframe of loans.
        value (int): Value to replace NaNs with.

    Returns:
        DataFrame: Dataframe where the missing values have been replaced by the number in the value paremeter.
    '''
    for col in df.columns:
        df[col] = df[col].fillna(value)

    return df

def memory_management(df):
    '''
    Function to drastically reduce the dataframe's size in memory by converting columns to their proper data types.

    TODO: Leave this for the end, no need to prematurely optimize. 
    '''
    pass

def drop_unnecessary_cols(df):
    '''
    Function to drop columns that are deemed to be unnecessary/unwanted for the model.

    Args:
        df (dataframe): Dataframe of loans.

    Returns:
        Dataframe: Returns the input dataframe with desired columns removed.
    '''
    drop_cols = ('zip_code', 'total_rec_prncp', 'total_rec_int', 'earliest_cr_line', 'term',
                 'last_pymnt_d', 'total_pymnt_inv', 'application_type')
    for col in drop_cols:
        df.drop(col, axis=1, inplace=True)
    return df

def exclude_loans_before_2010(df):
    '''
    Drop all loans issued before 2010. This is to remove the effect of the "great recession". 

    Args:
        df (dataframe): Dataframe of loans.

    Returns:
        Dataframe: Dataframe that only includes loans issued in January 2010 or later. 

    TODO: Should this be done? My model isn't designed to predict and prepare for black swan events.
          Users are understanding of this fact. Let's evaluate the models both with and without loans before 2010.
    '''
    mask = df['issue_d'] >= '2010-01-01'
    return df.loc[mask, :]

def clean_and_prepare_raw_data_for_model(df):
    '''
    Take in the raw dataframe containing all loan data and run through all functions required to prepare it for model training.

    Args:
        df (dataframe): Dataframe of loans.

    Returns:
        Dataframe: Returns the loan dataframe after all the data cleaning and feature engineering functions have been applied.

    TODO:
        This function currently relies on functions stored in feature-engineering.py. This is acceptable for working in the
        Jupyter notebook I have but I need to change the organization of my code later on.
    '''
    df = drop_loan_status(df)
    df = drop_joint_applicant_loans(df)
    df = fix_rate_cols(df)
    df.dropna(subset=['issue_d'], inplace=True)
    df = fix_date_cols(df)
    df.sort_values(by='issue_d', inplace=True)
    df = exclude_loans_before_2010(df)
    df = clean_loan_term_col(df)
    df = only_include_36_month_loans(df)
    df = clean_employment_length(df)
    # I doubt we need missing data boolean columns for tree models.
    df = create_missing_data_boolean_columns(df)
    df = fill_nas(df, value=-99)
    #df = add_issue_date_and_month(df) # Ditch this?
    df = add_supplemental_rate_data(df)
    df = create_rate_difference_cols(df)
    df = create_months_since_earliest_cl_col(df)
    #df = create_loan_life_months_col(df)
    df = change_data_types(df)
    df = create_dummy_cols(df)
    df = drop_unnecessary_cols(df)
    df.set_index('id', inplace=True)

    return df