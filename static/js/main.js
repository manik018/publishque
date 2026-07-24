document.addEventListener("DOMContentLoaded", () => {
    const sidebar = document.getElementById("mobile-sidebar");
    const openButtons = document.querySelectorAll("[data-sidebar-open]");
    const closeButtons = document.querySelectorAll("[data-sidebar-close]");

    if (!sidebar) {
        return;
    }

    const openSidebar = () => {
        sidebar.classList.remove("hidden");
        sidebar.setAttribute("aria-hidden", "false");
    };

    const closeSidebar = () => {
        sidebar.classList.add("hidden");
        sidebar.setAttribute("aria-hidden", "true");
    };

    openButtons.forEach((button) => button.addEventListener("click", openSidebar));
    closeButtons.forEach((button) => button.addEventListener("click", closeSidebar));
});
