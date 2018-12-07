describe('Test the SubtitleBackupStorage service', function() {
    var SubtitleBackupStorage = null;
    var videoId = 'video-id';
    var languageCode = 'en';
    var versionNumber = 5;
    var $window;

    beforeEach(module('amara.SubtitleEditor.subtitles.services'));

    beforeEach(inject(function($injector) {
        SubtitleBackupStorage = $injector.get('SubtitleBackupStorage');
        $window = $injector.get('$window');
    }));

    afterEach(function() {
        SubtitleBackupStorage.clearBackup();
    });

    it('should start without a backup', function() {
        expect(SubtitleBackupStorage.hasAnyBackup()).toEqual(false);
    });

    it('saves and restores backups', function() {
        SubtitleBackupStorage.saveBackup(videoId, languageCode, versionNumber, 'dfxp string');
        expect(SubtitleBackupStorage.hasBackup(videoId, languageCode, versionNumber)).toEqual(true);
        expect(SubtitleBackupStorage.getBackup(videoId, languageCode, versionNumber)).toEqual('dfxp string');
        // after the restore, we shouldn't still have a backup
        expect(SubtitleBackupStorage.hasBackup(videoId, languageCode, versionNumber)).toEqual(false);
    });

    it('saves backups with no versionNumber', function() {
        versionNumber = null;
        SubtitleBackupStorage.saveBackup(videoId, languageCode, versionNumber, 'dfxp string');
        expect(SubtitleBackupStorage.hasBackup(videoId, languageCode, versionNumber)).toEqual(true);
        expect(SubtitleBackupStorage.getBackup(videoId, languageCode, versionNumber)).toEqual('dfxp string');
    });

    it('only restores backups if the corresponding data matches', function() {
        SubtitleBackupStorage.saveBackup(videoId, languageCode, versionNumber, 'dfxp string');
        expect(SubtitleBackupStorage.hasBackup(videoId, languageCode, versionNumber + 1)).toEqual(false);
        expect(SubtitleBackupStorage.hasBackup(videoId, 'fr', versionNumber)).toEqual(false);
        expect(SubtitleBackupStorage.hasBackup('other-video-id', languageCode, versionNumber)).toEqual(false);
    });

    it('deletes backups', function() {
        SubtitleBackupStorage.saveBackup(videoId, languageCode, versionNumber, 'dfxp string');
        SubtitleBackupStorage.clearBackup();
        expect(SubtitleBackupStorage.hasBackup(videoId, languageCode, versionNumber + 1)).toEqual(false);
    });

    it('does not crash with invalid data', function() {
        window.localStorage.setItem('amara-subtitle-backup', 'invalid-data');
        expect(SubtitleBackupStorage.getBackup(videoId, languageCode, versionNumber)).toEqual(null);
    });
});

