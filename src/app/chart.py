import pandas as pd

import plotly.express as px

def precompute_df_sentiment(messages):
    df = pd.DataFrame(messages)
    df['date'] = pd.to_datetime(df['date'])
    df['date_r'] = df['date'].dt.round('5min')  # Round to the most precise interval: 5 minutes
    # so it will be faster to regroup the data and regenerate the chart

    # Get the dominant sentiment for each message
    df['dominant_sentiment'] = df[['negative', 'neutral', 'positive']].idxmax(axis=1)

    grouped = df.groupby(['date_r', 'dominant_sentiment']).size().unstack(fill_value=0).reset_index()
    df_long = pd.melt(grouped, id_vars=['date_r'], var_name='sentiment', value_name='count')

    return df_long


def generate_chart(df_long, interval):

    df_interval = df_long.copy()
    df_interval['date_r'] = df_interval['date_r'].dt.round(interval)

    # Sum the counts for each interval
    df_interval = df_interval.groupby(['date_r', 'sentiment']).sum().reset_index()

    fig = px.bar(df_interval, x='date_r', y='count', color='sentiment',
                 color_discrete_map={'neutral': '#eeeeee', 'negative': '#e74c3c', 'positive': '#2ecc71'},
                 labels={'date_r': '', 'count': 'Number of messages'})

    # Update the layout for dark background
    fig.update_layout(
        plot_bgcolor='#1f1f1f',  
        paper_bgcolor='#1f1f1f',
        font=dict(color='white'),
        yaxis=dict(gridcolor='gray'),
        title_text='Evolution of dominant sentiment', 
        title_x=0.5,

        # Update the legend
        legend=dict(
            orientation='h',  # Horizontal orientation
            yanchor='bottom', # Align to the bottom
            y=-0.45,  # Adjust vertical position
            xanchor='center', # Center the legend
            x=0.2,     # Place legend in the center horizontally
            bgcolor='rgba(0,0,0,0)'  # Transparent background for the legend
        )
    )

    return fig