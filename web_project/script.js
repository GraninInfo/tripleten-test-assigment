document.addEventListener('DOMContentLoaded', () => {
    const circle = document.getElementById('circle');
    const orangeBtn = document.getElementById('orangeBtn');
    const purpleBtn = document.getElementById('purpleBtn');
    const redHoverBtn = document.getElementById('redHoverBtn');
    const pinkHoverBtn = document.getElementById('pinkHoverBtn');

    let currentColor = 'green'; // Initial color

    // Function to update circle color on click
    const changeColor = (color) => {
        circle.style.backgroundColor = color;
        currentColor = color;
    };

    // Click event listeners
    orangeBtn.addEventListener('click', () => changeColor('orange'));
    purpleBtn.addEventListener('click', () => changeColor('white')); // bug with wrong color

    // Hover event listeners for red button
    // bug with non-working button
    // redHoverBtn.addEventListener('mouseover', () => {
    //     circle.style.backgroundColor = 'red';
    // });
    // redHoverBtn.addEventListener('mouseout', () => {
    //     circle.style.backgroundColor = currentColor;
    // });

    // Hover event listeners for pink button
    pinkHoverBtn.addEventListener('mouseover', () => {
        circle.style.backgroundColor = 'pink';
    });
    pinkHoverBtn.addEventListener('mouseout', () => {
        circle.style.backgroundColor = currentColor;
    });
});