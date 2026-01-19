import pandas as pd
import numpy as np


def nombre_formula(header: str, src_df: pd.DataFrame, *args) -> pd.DataFrame:
    """Generate name formula combining translation type and fiscal period"""
    try:
        df = pd.DataFrame(columns=[header])
        df[header] = (
            src_df['Translation Type'] + " " +
            pd.to_datetime(
                src_df['Fiscal Year'].astype(str) + '-' + src_df['Fiscal Period'].astype(str)
            ).dt.strftime('%b-%Y').str.lower()
        )
        return df
    except Exception as e:
        print(f"Error in nombre_formula: {e}")
        return pd.DataFrame(columns=[header])


def descripcion_formula(header: str, src_df: pd.DataFrame, *args) -> pd.DataFrame:
    """Generate description formula combining multiple fields"""
    df = pd.DataFrame(columns=[header])
    df[header] = ('M1/' + src_df['Unit'].astype(str) + '/' + src_df['Fiscal Year'].astype(str) + '/' + 
        src_df['Fiscal Period'].astype(str) + '/' + src_df['Contract Name'].astype(str) + '/' + 
        src_df['Vendor'].astype(str)
    )
    return df


def gl_account_split(header: str, src_df: pd.DataFrame, *args) -> pd.DataFrame:
    """Split GL Account by dash separator into specific components"""
    header_to_index = {
        "compania": 0,
        "Unidad": 1,
        "CC": 2,
        "ubicacion": 3,
        "cuenta": 4,
        "subcuenta": 5,
        "equipo": 6,
        "intercompania": 7,
    }
    
    idx = header_to_index.get(header)
    if idx is None:
        return pd.DataFrame()
    
    splitted = src_df["GL Account"].str.split("-", expand=True)
    
    if splitted.shape[1] <= idx:
        col_data = pd.Series([None] * src_df.shape[0])
    else:
        col_data = splitted[idx]
    
    return pd.DataFrame({header: col_data})


# Formula mappings dictionary
FORMULA_MAPPINGS = {
    "TC": None, 
    "Nombre": nombre_formula,
    "divisa": lambda header, src_df, *args: pd.DataFrame({header: src_df["Contract Currency"]}),
    "compania": gl_account_split,
    "Unidad": gl_account_split,
    "CC": gl_account_split,
    "ubicacion": gl_account_split,
    "cuenta": gl_account_split,
    "subcuenta": gl_account_split,
    "equipo": gl_account_split,
    "intercompania": gl_account_split,
    "debito": lambda header, src_df, *args: pd.DataFrame({
        header: np.where(
            src_df["Amount in Contract Currency"].astype(float) > 0,
            src_df["Amount in Contract Currency"].astype(float),
            0
        )
    }),
    "credito": lambda header, src_df, *args: pd.DataFrame({
        header: np.where(
            src_df["Amount in Contract Currency"].astype(float) < 0,
            np.abs(src_df["Amount in Contract Currency"].astype(float)),
            0
        )
    }),
    "debito_convertido": "",
    "credito_convertido": "",
    "descripcion": descripcion_formula
}

# Cell number formatting
CELL_NUMBER_FORMAT = {
    "TC": '_-* #,##0.0000_-;-* #,##0.0000_-;_-* "-"??_-;_-@_-',
    "debito": '_-* #,##0.00_-;-* #,##0.00_-;_-* "-"??_-;_-@_-',
    "credito": '_-* #,##0.00_-;-* #,##0.00_-;_-* "-"??_-;_-@_-',
    "debito_convertido": '_-* #,##0.00_-;-* #,##0.00_-;_-* "-"??_-;_-@_-',
    "credito_convertido": '_-* #,##0.00_-;-* #,##0.00_-;_-* "-"??_-;_-@_-'
}


def handle_formula(header: str, src_df: pd.DataFrame, *args) -> pd.DataFrame:
    """Handle formula processing for a given header"""
    formula_func = FORMULA_MAPPINGS.get(header)
    
    if callable(formula_func):
        return formula_func(header, src_df, *args)  
    
    return pd.DataFrame()