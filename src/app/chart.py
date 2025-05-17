import pandas as pd
import plotly.express as px


def generate_chart(messages, interval):

    df = pd.DataFrame(messages)
    df['date'] = pd.to_datetime(df['date'])
    df['date_r'] = df['date'].dt.round(interval)

    # Get the dominant sentiment for each message
    df['dominant_sentiment'] = df[['negative', 'neutral', 'positive']].idxmax(axis=1)

    grouped = df.groupby(['date_r', 'dominant_sentiment']).size().unstack(fill_value=0).reset_index()
    df_sentiment = pd.melt(grouped, id_vars=['date_r'], var_name='sentiment', value_name='count')

    fig = px.bar(df_sentiment, x='date_r', y='count', color='sentiment',
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
            orientation='h',
            yanchor='bottom',
            y=-0.45, 
            xanchor='center',
            x=0.2,    
            bgcolor='rgba(0,0,0,0)'
        )
    )

    return fig