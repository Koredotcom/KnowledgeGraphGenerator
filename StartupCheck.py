import os
from log.Logger import Logger

logger = Logger()


class StartupCheck(object):
    """
    StartupCheck
    """

    @staticmethod
    def create_directory(directory_path):
        """
        create_download_directory if not exist
        """
        try:
            if not os.path.exists(directory_path):
                os.makedirs(directory_path)
                logger.info('Auto Ontology Directory: Created {0}'.format(directory_path))
            else:
                logger.info('Auto Ontology: Already exist{0}'.format(directory_path))
            return True
        except:
            logger.error('Error!! in creating Auto Ontology directory {0}'.format(directory_path))
            return False

    @classmethod
    def initialize(cls, startup_checklist):
        """
        perform startup_check
        """
        try:
            logger.info('Started..... startup checklist')
            status = True
            for directory in startup_checklist:
                status = status and StartupCheck.create_directory(directory)
            return status
        finally:
            logger.info('Finished.... startup checklist')


if __name__ == '__main__':
    StartupCheck.initialize([])
