var dagcomponentfuncs = (window.dashAgGridComponentFunctions = window.dashAgGridComponentFunctions || {});

dagcomponentfuncs.RenderHTML = function (props) {
    const { data, setData } = props;

    const handleClick = (event) => {
        const target = event.target;

        if (target.classList.contains('user-icon')) {
            setData({ filterAccount: data.account }); // Use a different key to avoid conflict

        } else if (target.classList.contains('similar-icon')) {
            setData({ showSimilar: true }); // Signal to show similar messages

        } else if (target.classList.contains('location-icon')) {
            setData({ zoomLoc: [target.dataset.lat, target.dataset.lon, target.title] });
        }
    };

    return React.createElement(
        'div',
        {
            dangerouslySetInnerHTML: { __html: props.value },
            onClick: handleClick // Add the click listener to the container
        }
    );
};
