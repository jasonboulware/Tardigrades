# Amara, universalsubtitles.org
#
# Copyright (C) 2018 Participatory Culture Foundation
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see
# http://www.gnu.org/licenses/agpl-3.0.html.

"""
Older django versions didn't support the index_together attribute, so we had
to manually create them in the setup_indexes scripts.

When we switched to django1.7, we gained the ability to handle these indexes
natively.  This migration handles moving to the native indexes by finding the
old index and renaming it to the standard django name.
"""

from collections import defaultdict

from django.db import migrations

class ConvertLegacyIndexTogether(migrations.AlterIndexTogether):
    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        new_apps = to_state.apps
        new_model = new_apps.get_model(app_label, self.name)
        if not self.allow_migrate_model(schema_editor.connection.alias, new_model):
            return

        migrated_indexes = []
        unmigrated_indexes = []
        existing_indexes = self.find_existing_indexes(schema_editor, new_model)
        for fields in self.index_together:
            if self.migrate_old_index(schema_editor, new_model, fields,
                                      existing_indexes):
                migrated_indexes.append(fields)
            else:
                unmigrated_indexes.append(fields)
        # When running migrate from a fresh DB, we won't have the indexes that
        # were created using setup_indexes.  Have Django create those from
        # scratch.
        if unmigrated_indexes:
            schema_editor.alter_index_together(
                new_model, migrated_indexes, unmigrated_indexes)

    def find_existing_indexes(self, schema_editor, model):
        cursor = schema_editor.connection.cursor()
        cursor.execute('SHOW INDEXES FROM {} WHERE Non_unique=1'.format(
            model._meta.db_table))
        rows = cursor.fetchall()
        # sort rows by key name/column index.
        # (SHOW INDEXES doesn't support ORDER BY)
        rows = sorted(rows, key=lambda r: (r[2], r[3]))

        # map index names to column lists
        indexes = defaultdict(list)
        for row in rows:
            indexes[row[2]].append(row[4])

        # map columns to indexes
        existing_indexes = defaultdict(list)
        for name, columns in indexes.items():
            existing_indexes[tuple(columns)].append(name)
        return existing_indexes

    def migrate_old_index(self, schema_editor, model, fields, existing_indexes):
        columns = tuple(self.field_to_column(model, name) for name in fields)
        old_index_names = existing_indexes[columns]
        if not old_index_names:
            return False
        new_index_name = schema_editor._create_index_name(model, columns,
                                                          suffix="_idx")
        self.rename_index(schema_editor, model, old_index_names[0],
                          new_index_name)
        for old_index_name in old_index_names[1:]:
            # If our code created 2 indexes by accident, delete the old one
            self.delete_index(schema_editor, model, old_index_name)
        return True

    def field_to_column(self, model, field):
        return model._meta.get_field(field).column

    def rename_index(self, schema_editor, model, old_name, new_name):
        schema_editor.execute("ALTER TABLE {} RENAME INDEX {} to {}".format(
                              model._meta.db_table, old_name, new_name))

    def delete_index(self, schema_editor, model, name):
        schema_editor.execute("ALTER TABLE {} DELETE INDEX {}".format(
                              model._meta.db_table, name))

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        # No need to do anything here, just continue to use the new index
        # names
        return
