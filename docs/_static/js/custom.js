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
})();
