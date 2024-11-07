from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime
from random import randint

def _choose_best_model(ti):
    # Pull accuracies for each model
    accuracies = {
        'A': ti.xcom_pull(task_ids='training_model_A'),
        'B': ti.xcom_pull(task_ids='training_model_B'),
        'C': ti.xcom_pull(task_ids='training_model_C')
    }
    
    # Find the model with the highest accuracy
    best_model = max(accuracies, key=accuracies.get)
    best_accuracy = accuracies[best_model]
    
    # Push best model to XCom
    ti.xcom_push(key='best_model', value=best_model)
    
    # Determine which branch to take
    if best_accuracy > 8:
        return 'is_accurate'
    return 'is_inaccurate'

def _training_model(model):
    print(f"Training model {model}")
    # Simulate training by returning a random accuracy score
    return randint(1, 10)

def _log_accurate_model(ti):
    # Retrieve the best model from XCom
    best_model = ti.xcom_pull(task_ids='choose_best_model', key='best_model')
    if best_model:
        print(f"Accurate Model Selected: Model {best_model}")
    else:
        print("No model was accurate enough.")

with DAG("my_dag",
    start_date=datetime(2023, 1, 1), 
    schedule_interval='@daily', 
    catchup=False) as dag:

    training_model_tasks = [
        PythonOperator(
            task_id=f"training_model_{model_id}",
            python_callable=_training_model,
            op_kwargs={"model": model_id}
        ) for model_id in ['A', 'B', 'C']
    ]

    choose_best_model = BranchPythonOperator(
        task_id="choose_best_model",
        python_callable=_choose_best_model
    )

    accurate = BashOperator(
        task_id="is_accurate",
        bash_command="echo 'The best model is: {{ ti.xcom_pull(task_ids='choose_best_model', key='best_model') }} with high accuracy'"
    )

    inaccurate = BashOperator(
        task_id="is_inaccurate",
        bash_command="echo 'No model met the accuracy threshold'"
    )

    log_accurate_model = PythonOperator(
        task_id="log_accurate_model",
        python_callable=_log_accurate_model,
        trigger_rule="none_failed_min_one_success"
    )

    # Set dependencies
    training_model_tasks >> choose_best_model >> [accurate, inaccurate] >> log_accurate_model
