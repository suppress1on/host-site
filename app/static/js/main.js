document.addEventListener('DOMContentLoaded', () => {
    console.log('Main page JavaScript loaded and ready!');

    const serviceItems = document.querySelectorAll('.service-list li');
    serviceItems.forEach(item => {
        item.style.cursor = 'pointer';
        item.addEventListener('click', () => {
            alert(`Вы выбрали услугу: "${item.textContent.trim()}"`);
        });
    });
});