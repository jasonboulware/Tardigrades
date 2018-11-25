$(function() {
    $('.dropdown-toggle').each(function() {
        var link = $(this);
        var dropdown = link.closest('.dropdown');

        function openMenu() {
            dropdown.addClass('open');
            link.attr("aria-expanded", "true");
        }
        function closeMenu() {
            dropdown.removeClass('open');
            link.attr("aria-expanded", "false");
        }
        link.click(function(evt) {
            if(dropdown.hasClass('open')) {
                closeMenu();
            } else {
                openMenu();
            }
            evt.preventDefault();
            return false;
        });
        $('body').click(function(evt) {
            if(dropdown.hasClass('open') && dropdown.has(evt.target).length == 0) {
                closeMenu();
                evt.preventDefault();
                return false;
            }
        });
    });
});
