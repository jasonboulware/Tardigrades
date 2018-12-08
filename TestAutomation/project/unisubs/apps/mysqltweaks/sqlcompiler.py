from django.db.backends.mysql import compiler

class PatchedSQLCompiler(compiler.SQLCompiler):
    def get_from_clause(self):
        result, params = super(PatchedSQLCompiler, self).get_from_clause()
        if getattr(self.query, 'force_index', False):
            result[0] += ' FORCE INDEX({})'.format(
                self.connection.ops.quote_name(self.query.force_index))
        return result, params
