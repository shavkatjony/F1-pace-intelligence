''' guys we are here build the very boring and hard thing ,it is feel like going a bazaar with your auntie to bu a pants,and you probably try 20+ of them and your auntie will ask 85% discount from seller that saying it is fixed price.
to understand the in the column level , probably learn the how f1 works , 
and then the what is this project probably ,and then explore some columns if you have enough neurons avalable for today and 
if you are reading this after the midday , you need a redbull for that and after drink wait 20 minutes to fully absorb ,
and then you will have temporary energy ,
to understand what how much dat we are talking about not what kind ,
if you want to understand in the column and its type level , start it in the morning ,
your bran might thank you
if you add some caffeine it will be better . so good lack '''

# |================================================================================================\
# Welcome to data engineering part of the project 
# shavkhatjon building the duckDB warehouse from the sql files, 
# and we run the queries on it in october 18 ,on sunday, time: 1:29 AM

#=======================================================================================

from pathlib import Path

import duckdb
import pandas as pd

def render(sql: str, param: dict) -> str:
    """Fill {{name}} placeholders, the same style dbt uses."""
    for name, value in params.items():
        sql = sql.replace("{{ " + name + "}}", str(value))
    if "{{" in sql:
        raise ValueError(f"unfilled placeholder in SQL: {sql[sql.index('{{'):][:40]}")
    return sql