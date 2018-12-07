# ########################################################
# S3FileField.py
# Extended FileField and ImageField for use with Django and Boto.
#
# Required settings:
#    USE_AMAZON_S3 - Boolean, self explanatory
#    AWS_ACCESS_KEY_ID - String
#    AWS_SECRET_ACCESS_KEY - String
#
# ########################################################
from fields import S3EnabledImageField, S3EnabledFileField
