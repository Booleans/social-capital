import pandas as pd
from datetime import datetime as dt

def load_data(csv_files, columns, number_of_rows=None):
    '''
    Function to take a list of CSV files that contain the data on Lending Club's loans and 
    concatenate them into one dataframe. 

    Args:
        csv_files (list): List of CSV files that contain the data. Files should be stored in the /data
        folder and omit the '.csv' at the end of the file name. For example, 'data/LoanStats3a_securev1.csv'
        will be in the list as 'LoanStats3a_securev1'.

        columns (list): List of column names that should be used in the dataframe. Certain columns should be
        excluded due to the fact they would not have been available at the time the loan was issued.
        The list of accetable columns is generated by the the file `columns.py` in the src folder.

        number_of_rows (int): The number of rows to load from each CSV file. This is used to load in smaller 
        amounts of data for testing purposes. By default, number_of_rows is None, which loads all data. 

    Returns:
        DataFrame: Returns a dataframe containing all loans contained within the list of CSV files. 
    '''
    loan_data = []
    for file in csv_files:    
        data = pd.read_csv('data/' + file + '.csv', header=1, low_memory=False, na_values='n/a',
                           usecols=columns, nrows=number_of_rows) 
        loan_data.append(data)
    loans = pd.concat(loan_data)
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
    df = df[(df['loan_status'] == 'Charged Off') | (df['loan_status'] == 'Fully Paid')]
    return df

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
    df = df[df['application_type'].str.upper() == "INDIVIDUAL"]
    return df

def fix_rate_cols(df):
    '''
    Fix the data types of columns that are related to interest rates. They were read in as strings instead of floats due to
    the fact they contain the symbol for percent. For example, a loan with interest rate '16.37%'. 

    Args:
        df (dataframe): Dataframe of loans.

    Returns:
        DataFrame: Returns dataframe where the interest rate columns that were incorrectly read in as strings
        have been converted to floats.
    '''
    # Columns that end with % were read in as strings instead of floats. We need to remove the % and change data types.
    rate_cols = ['int_rate', 'revol_util']
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
    df = df[df['term'] == 36]
    return df

def exclude_recent_loans(df, min_age_months):
    '''
    '''
    #df = df[df['issue_d'] < cutoff_date]
    df.drop(labels=['issue_d'], axis=1, inplace=True)
    return df

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
    pass

def drop_unnecessary_cols(df):
    '''
    Function to drop columns that are deemed to be unnecessary/unwanted for the model.

    Args:
        df (dataframe): Dataframe of loans.

    Returns:
        Dataframe with desired columns removed.
    '''
    drop_cols = ('zip_code', 'total_rec_prncp', 'total_rec_int', 'earliest_cr_line', 'term',
                 'last_pymnt_d', 'total_pymnt_inv', 'application_type')
    for col in drop_cols:
        df.drop(col, axis=1, inplace=True)
    return df

def exclude_loans_before_2010(df):
    '''
    Drop all loans issued before 2010. This is to remove the effect of the great recession. 

    Todo: Should this be done? My model isn't designed to predict and prepare for black swan events. 
    '''
    loans_2010_and_later = df[df['issue_d'] >= '2010-01-01']
    return loans_2010_and_later
