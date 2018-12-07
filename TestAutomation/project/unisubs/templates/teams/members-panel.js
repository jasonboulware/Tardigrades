(function(){

    var EDIT_SELECTOR = '.edit-role';

    var EditRoleDialog = Class.$extend({
        __init__:function(pk, username, fullname, teamSlug){
            this.pk = pk;
            this.username = username;
            this.fullname = fullname;
            this.teamSlug = teamSlug;
            this.hide = _.bind(this.hide, this);
            this.hideAndRedirect = _.bind(this.hideAndRedirect, this);
            this.save = _.bind(this.save, this);
            this.show = _.bind(this.show, this);
        },
        loadInfo: function(){
            TeamsApiV2.member_role_info(
                this.teamSlug,
                this.pk,
                this.show);
        },
        show: function(res){
            res['username'] = this.username;
            res['fullname'] = this.fullname;
            this.el = ich.editRoleDialog(res);
            hideEdit = this.hide;
            $body = $('body');

            $('select option[value="' + res['current_role'] + '"]', this.el).attr('selected', 'selected');

            $body.append('<div class="well"></div>');
            $target = $('div.modal', $body.append(this.el));
            $target.show();
            $select = $('select', this.el);

            $('.chzn-select', this.el).chosen();
            $('a.action-save', this.el).click(this.save);
            $('a.action-close', this.el).click(function() {
                hideEdit($target);
            });

            $select.change(this.buildRestrictions);
            $select.trigger('change');

            $target.click(function(event){
                event.stopPropagation();
            });

            $('html').bind('click.modal', function() {
                hideEdit($target);
            });
        },
        buildRestrictions: function() {
            var val = $(this).val();
            var $lang = $('#language-restriction');
            var $proj = $('#project-restriction');

            var lang_count = $('option', $lang).length;
            var proj_count = $('option', $proj).length;

            if (val == 'manager') {
                if (lang_count) { $lang.show(); }
                if (proj_count) { $proj.show(); }
            } else if (val == 'contributor') {
                $lang.hide();
                $proj.hide();
            } else if (val == 'admin') {
                $lang.hide();
                if (proj_count) { $proj.show(); }
            }
        },
        save: function(e){
            e.preventDefault();
            var languages = $('select.langs', this.el) .val();
            var projects = $('select.projects', this.el) .val();
            var role = $('select.roles', this.el).val();
            TeamsApiV2.save_role(
                this.teamSlug,
                this.pk,
                role,
                projects,
                languages,
                this.hideAndRedirect);
            return false;
        },
        hide: function(e){
            this.el.remove();
            $('div.well').remove();
            $('html').unbind('click.modal');
            return false;
        },
        hideAndRedirect: function(e) {
            this.el.remove();
            $('div.well').remove();
            $('html').unbind('click.modal');
            if (window.roleSavedURL) {
                window.location = window.roleSavedURL;
            }
            return false;
        }
    });

    $('a.edit-role').click(function(e) {
        e.preventDefault();
        var pk = $(e.target).data('member-pk');
        var username = $(e.target).data('member-username');
        var fullname = $(e.target).data('member-fullname');
        var teamSlug = $(e.target).data('team-slug');
        var dialog = new EditRoleDialog(pk, username, fullname, teamSlug);
        dialog.loadInfo();
        return false;
    });
})();
