#pragma once
#include "Project.h"
#include <QMainWindow>
#include <QMap>
#include <QStringList>

class QCheckBox;
class QComboBox;
class QLineEdit;
class QPlainTextEdit;
class QLabel;
class QTabWidget;

class MainWindow : public QMainWindow {
public:
    explicit MainWindow(QWidget* parent=nullptr);
private:
    struct AgentRow { QCheckBox* enabled=nullptr; QComboBox* model=nullptr; };
    QString root_;
    ProjectConfig current_;
    QMap<QString,AgentRow> agents_;
    QStringList availableModels_;
    QLineEdit *path_=nullptr, *allModel_=nullptr;
    QPlainTextEdit *brief_=nullptr, *networkAllow_=nullptr, *networkDeny_=nullptr, *paths_=nullptr, *pathsDeny_=nullptr, *shares_=nullptr, *sharesDeny_=nullptr, *devices_=nullptr, *preview_=nullptr;
    QComboBox *internet_=nullptr, *read_=nullptr, *edit_=nullptr, *bash_=nullptr, *external_=nullptr, *gitPush_=nullptr, *gitForce_=nullptr, *gitCommit_=nullptr, *usb_=nullptr, *firmware_=nullptr, *gitMode_=nullptr;
    QComboBox *overrideRole_=nullptr, *overrideRead_=nullptr, *overrideEdit_=nullptr, *overrideBash_=nullptr, *overrideWeb_=nullptr;
    QJsonObject localOverrides_;
    QCheckBox *unattended_=nullptr;
    QLineEdit *remote_=nullptr, *host_=nullptr, *port_=nullptr, *sshUser_=nullptr, *sshKey_=nullptr, *repo_=nullptr, *author_=nullptr, *email_=nullptr, *branch_=nullptr;
    QLabel *status_=nullptr;
    QTabWidget *tabs_=nullptr;
    QWidget* makeProjectTab();
    QWidget* makeAgentsTab();
    QWidget* makePermissionsTab();
    QWidget* makeGitTab();
    QWidget* makePreviewTab();
    void openProject();
    void chooseFolder();
    void showConfig();
    bool collect(ProjectConfig& output);
    void saveProject();
    void previewChanges();
    void loadModels();
    void applyBulkModel();
    void gitApply();
    void gitCheck();
    void loadOverride();
    void saveOverride();
    void setStatus(const QString& message,bool bad=false);
};
