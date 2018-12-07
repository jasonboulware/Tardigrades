from django.db.models.query import QuerySet


class LoadRelatedQuerySet(QuerySet):
    def __len__(self):
        val = super(LoadRelatedQuerySet, self).__len__()
        self.update_result_cache()
        return val

    def _fill_cache(self, num=None):
        super(LoadRelatedQuerySet, self)._fill_cache(num)
        self.update_result_cache()

    def update_result_cache(self):
        """
        In this method check objects in self._result_cache and add related to
        some attribute
        """
        raise Exception('Not implemented')
