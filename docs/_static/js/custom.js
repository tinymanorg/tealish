"use strict";

(function () {
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
      document.documentElement.classList.add("menu-open");
      sidebarContainer.classList.add("visible");
    }
    function closeSidebar() {
      document.documentElement.classList.remove("menu-open");
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
