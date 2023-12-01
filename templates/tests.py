import pandas as pd
import numpy as np
from sklearn import metrics
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split 
import plotly.express as px
import plotly.graph_objects as go


def scatter_plot_interp(data, columns:list[str], show=True):
    fig = px.scatter(data, y=columns)
    fig.update_traces(marker_size=10)
    fig.update_layout(template="simple_white")
    if show:
      fig.show()
    return fig

def get_RMSE(y_true, y_predicted):
    RMSE = np.sqrt(np.mean((y_true - y_predicted)**2))
    return RMSE

def regression_results(y_true, y_pred):

    # Regression metrics
    mse=metrics.mean_squared_error(y_true, y_pred) 
    median_absolute_error=metrics.median_absolute_error(y_true, y_pred)
    r2=metrics.r2_score(y_true, y_pred)

    print('r^2: ', round(r2,4))
    print('MAE: ', round(median_absolute_error,4))
    print('MSE: ', round(mse,4))
    print('RMSE: ', round(np.sqrt(mse),4))


#---------------- interpolation
def interpolation_tests():
    index = [1,2,3,4,5,6,7,8,9,10,11]
    data = {
        "full_data" : [1,2,0,13,4,10,19,15,13,21,27],
        "missing_data" : [1,2,0,np.NaN,4,np.NaN,19,15,13,np.NaN,27]
    }
    data = pd.DataFrame(index = index, data = data)

    indices_of_missing_points = data.loc[data["missing_data"].isna()].index
    indices_of_present_points = data.loc[data["missing_data"].notna()].index
    data["interpolated_data"] = data["missing_data"].interpolate()

    y_true = data.loc[indices_of_missing_points, "full_data"]
    y_predicted = data.loc[indices_of_missing_points, "interpolated_data"]
    RMSE = get_RMSE(y_true, y_predicted)
    fig = scatter_plot_interp(data, ["full_data", "interpolated_data"])


#----------- Rf and linear models
def linear_models():
    df_dwd = pd.read_parquet(r"assets\data\dwd_diepholz_1996_2023_missing_placeholders.parquet")
    df_dwd["date_time"] = pd.to_datetime(df_dwd["date_time"])
    indices_of_missing_values = df_dwd.loc[df_dwd["tair_2m_mean"] == -999.99, "tair_2m_mean"].index
    df_dwd.loc[indices_of_missing_values, "tair_2m_mean"] = np.NaN

    df_dwd_noNA = df_dwd.loc[:,["SWIN","rH", "pressure_air", "wind_speed", "precipitation", "tair_2m_mean", "date_time"]].dropna()
    # mean for most data:
    df_dwd_hourly_noNA = df_dwd_noNA.loc[:,["SWIN","rH", "pressure_air", "wind_speed","tair_2m_mean", "date_time"]].resample(rule="1h", on="date_time").mean().dropna()
    # sum for precipitation data:
    df_dwd_hourly_noNA["precipitation"] = df_dwd_noNA.loc[:,["precipitation", "date_time"]].resample(rule="1h", on="date_time").sum().dropna()

    x = df_dwd_hourly_noNA.loc[:,["SWIN","rH", "pressure_air", "wind_speed", "precipitation"]]
    y = df_dwd_hourly_noNA.loc[:,["tair_2m_mean"]]

    # Now we go an split the data into training and testing data:
    X_train, X_test, y_train, y_test = train_test_split( 
        x, y, test_size=0.3, random_state=101) 

    # Finally we do the full pipeline of 
    # creating the model, fitting it, and scoring:
    rf_model = RandomForestRegressor(random_state=42, n_estimators=12, n_jobs=10)
    rf_model.fit(X_train, y_train.values.ravel())
    rf_model.score(X_test, y_test)
    y_hat_rf = rf_model.predict(X_test)
    regression_results(y_test, y_hat_rf)

    #---- test for hourly data
    indices_for_gap = df_dwd_hourly_noNA.iloc[505:529, :].index
    gapped_data_hourly = df_dwd_hourly_noNA.copy()
    gapped_data_hourly.loc[indices_for_gap, "tair_2m_mean"] = np.NaN
    x_hourly = gapped_data_hourly.loc[indices_for_gap,["SWIN","rH", "pressure_air", "wind_speed", "precipitation"]]
    y_true = df_dwd_hourly_noNA.loc[indices_for_gap, "tair_2m_mean"]


    print("---- interpolation:")
    interpolated_data = gapped_data_hourly["tair_2m_mean"].interpolate()
    regression_results(y_true, interpolated_data[indices_for_gap])

    print("---- multiple linear regression:")
    linearModel = LinearRegression()
    linearModel.fit(X_train,y_train)
    y_hat_linear = linearModel.predict(x_hourly)
    regression_results(y_true, y_hat_linear)

    print("---- Random Forest:")
    y_hat_rf = rf_model.predict(x_hourly)
    regression_results(y_true, y_hat_rf)
    

df_dwd = pd.read_parquet(r"assets\data\dwd_diepholz_1996_2023_missing_placeholders.parquet")
df_dwd["date_time"] = pd.to_datetime(df_dwd["date_time"])
df_dwd = df_dwd.set_index("date_time")
indices_of_missing_values = df_dwd.loc[df_dwd["tair_2m_mean"] == -999.99, "tair_2m_mean"].index
df_dwd.loc[indices_of_missing_values, "tair_2m_mean"] = np.NaN
df_dwd_ta_hourly = df_dwd["tair_2m_mean"].resample("1h").mean()


def visualize_quantiles(x:pd.Series, q_low:float, q_high:float):
    import scipy.stats as stats
    x_mean = x.mean()
    x_sd = x.std()
    y = stats.norm.pdf(x.sort_values(), x_mean, x_sd) # This function creates the y-values of the normal distribution given our data, the mean and the standard deviation
    qh = x.quantile(q_high) # here we calculate the higher quantile threshold
    ql = x.quantile(q_low) # here we calculate the lower quantile threshold 
    fig = px.scatter(x=x.sort_values(),y=y)
    fig.add_trace(
        go.Scatter(
            x=[ql, ql],
            y = [0,max(y)],
            mode="lines",
            name=f"{q_low*100}% quantile"
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[qh, qh],
            y = [0,max(y)],
            mode="lines",
            name=f"{q_high*100}% quantile"
        )
    )
    fig.show()

visualize_quantiles(df_dwd.tair_2m_mean, 0.05, 0.95)

def peak_over_threshold(X:pd.Series, prob):

    print(f'Extremes detection using peak over threshold method at: {prob} percentile')
    df = pd.DataFrame(index=X.index, data = {
        "data": X,
        "extreme_low":  X < X.quantile(q=1-prob),
        "extreme_high":  X > X.quantile(q=prob)
    })
    plot_extremes(df, "extreme_high", "extreme_low")  
  
  
def plot_extremes(data:pd.DataFrame, extr_high_col:str, extr_low_col:str):
    extr_high_data = data.loc[data[extr_high_col]==True, "data"]
    extr_low_data = data.loc[data[extr_low_col]==True, "data"]
    
    fig = go.Figure()
    fig.add_traces(    
        go.Scatter(
            x=data.index, 
            y=data["data"],
            mode="markers",
            name="no extreme",
            marker_color="black"
            )
    ),
    fig.add_traces(
        go.Scatter(
            x = extr_high_data.index,
            y = extr_high_data,
            name="extr. high",
            mode="markers",
            marker=dict(
                color='red',
                size=5,
            ),
            showlegend=True
        )
    )
    fig.add_traces(
        go.Scatter(
            x = extr_low_data.index,
            y = extr_low_data,
            name="extr. low",
            mode="markers",
            marker=dict(
                color='LightSkyBlue',
                size=5
            ),
            showlegend=True
        )
    )
    fig.show()
    
peak_over_threshold(df_dwd_ta_hourly, 0.95)