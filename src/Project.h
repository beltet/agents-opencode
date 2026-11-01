#pragma once
#include <QJsonObject>
#include <QString>
#include <QStringList>
struct ProjectConfig {
    QStringList agents;
    QJsonObject models;
    QJsonObject policy;
    QJsonObject git;
    QString brief;
};
namespace Project {
QStringList availableRoles();
QJsonObject defaultPolicy();
ProjectConfig defaultConfig();
bool load(const QString& root, ProjectConfig& data, QString& error);
QJsonObject toJson(const ProjectConfig& data);
QJsonObject openCodeConfig(const QString& root, const ProjectConfig& data, QString& error);
QString preview(const QString& root, const ProjectConfig& data, QString& error);
bool save(const QString& root, const ProjectConfig& data, QString& error);
}
