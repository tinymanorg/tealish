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
    const contentsMenuButton = document.querySelector("#contents-menu-button");
    const sidebarCloseButton = document.querySelector("#sidebar__close-button");
    const sidebarOverlay = document.querySelector("#sidebar__overlay");
    const sidebarContainer = document.querySelector(".sphinxsidebar");

    contentsMenuButton.addEventListener("click", () => {
      openSidebar();
    });
    sidebarCloseButton.addEventListener("click", () => {
      closeSidebar();
    });
    sidebarOverlay.addEventListener("click", () => {
      closeSidebar();
    });

    function openSidebar() {
      sidebarContainer.classList.add("visible");
    }
    function closeSidebar() {
      sidebarContainer.classList.remove("visible");
    }
  });
})();
