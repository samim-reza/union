document.querySelectorAll('.bar-fill').forEach((bar) => {
    const width = bar.style.width;
    bar.style.width = '0%';
    requestAnimationFrame(() => {
        bar.style.width = width;
    });
});
