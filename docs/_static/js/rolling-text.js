(() => {
  window.addEventListener("DOMContentLoaded", () => {
    const rollingContent = document.querySelector("#rolling-content");
    const list = document.querySelector(".rolling-content__list");
    const items = Array.from(list.children).map(li => li.textContent);

    const itemsWidth = list.getBoundingClientRect().width;

    const howMany = Math.ceil((window.innerWidth * 2) / itemsWidth);

    console.log({items, howMany})

    Array(Math.max(3, howMany) * items.length)
      .fill(0)
      .map((_, index) => items[index % items.length])
      .forEach((text) => {
        const li = document.createElement('li');
        li.textContent = text;

        list.appendChild(li);
      })

    rollingContent.classList.add("start");
  });
})();
