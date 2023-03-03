"use strict";

(function () {
  const documentElement = document.documentElement;
  const currentPath = window.location.pathname;
  const indexHtmlFileName = "index.html";

  if (
    currentPath.slice(currentPath.length - indexHtmlFileName.length) ===
    indexHtmlFileName
  ) {
    documentElement.classList.add("index-page");
  }

  // as the script is added to the head, we need to wait until the dom is loaded
  window.addEventListener("DOMContentLoaded", () => {
    // sidebar toggle for smaller screens
    const sidebarOverlay = document.querySelector("#sidebar__overlay");
    const sidebarContainer = document.querySelector(".sphinxsidebar");

    for (let contentsButton of document.querySelectorAll(
      "#contents-menu-button"
    )) {
      contentsButton.addEventListener("click", () => {
        openSidebar();
      });
    }

    sidebarOverlay.addEventListener("click", () => {
      closeSidebar();
    });

    function openSidebar() {
      sidebarContainer.classList.add("visible");
    }
    function closeSidebar() {
      sidebarContainer.classList.remove("visible");
    }

    const scrollHandler = throttle(() => {
      if (window.scrollY > 0) {
        document.documentElement.classList.add("scrolled");
      } else {
        document.documentElement.classList.remove("scrolled");
      }
    });

    window.addEventListener("scroll", scrollHandler);
  });

  function throttle(fn) {
    let lastArgs;
    let lastContext;
    let inCooldownState = false;

    return function throttled() {
      if (inCooldownState) {
        lastContext = this;
        lastArgs = arguments;
        return;
      }

      inCooldownState = true;
      fn.apply(this, arguments);

      window.requestAnimationFrame(() => {
        inCooldownState = false;

        if (lastArgs) {
          throttled.apply(lastContext, lastArgs);
          lastContext = null;
          lastArgs = null;
        }
      });
    };
  }
})();
