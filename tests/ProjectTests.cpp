#include "../src/Project.h"
#include <QtTest/QTest>
#include <QTemporaryDir>
#include <QDir>
#include <QFile>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>

class ProjectTests : public QObject {
    Q_OBJECT
private slots:
    void embeddedProfiles(){
        auto roles=Project::availableRoles();
        QCOMPARE(roles.size(),23);
        QVERIFY(roles.contains("orchestrator"));
        QVERIFY(roles.contains("verification-engineer"));
        QVERIFY(roles.contains("code-reviewer"));
    }
    void saveAndReload(){
        QTemporaryDir tmp; QVERIFY(tmp.isValid());
        auto c=Project::defaultConfig();
        c.agents={"orchestrator","software-engineer","verification-engineer"};
        c.models={{"orchestrator","opencode/model-a"},{"software-engineer","local/coder"},{"verification-engineer","opencode/model-b"}};
        c.brief="# Testprojekt\n\nEn Qt-applikation med tester.\n";
        QString err; QVERIFY2(Project::save(tmp.path(),c,err),qPrintable(err));
        QVERIFY(QFile::exists(tmp.filePath("opencode.json")));
        QVERIFY(QFile::exists(tmp.filePath(".opencode/agents/orchestrator.md")));
        QFile instructions(tmp.filePath(".opencode/agents/orchestrator.md"));
        QVERIFY(instructions.open(QIODevice::ReadOnly));
        QVERIFY(instructions.readAll().contains("Adaptive primary orchestrator"));
        QVERIFY(QFile::exists(tmp.filePath(".agents-opencode/TEAM_REGISTRY.md")));
        ProjectConfig read; QVERIFY2(Project::load(tmp.path(),read,err),qPrintable(err));
        QCOMPARE(read.brief,c.brief);
        QCOMPARE(read.agents.size(),3);
        QCOMPARE(read.models.value("software-engineer").toString(),QString("local/coder"));
        QFile f(tmp.filePath("opencode.json")); QVERIFY(f.open(QIODevice::ReadOnly));
        auto o=QJsonDocument::fromJson(f.readAll()).object();
        QCOMPARE(o.value("default_agent").toString(),QString("orchestrator"));
        auto agents=o.value("agent").toObject();
        QCOMPARE(agents.value("orchestrator").toObject().value("mode").toString(),QString("primary"));
        auto reviewer=agents.value("verification-engineer").toObject();
        QCOMPARE(reviewer.value("mode").toString(),QString("subagent"));
        QCOMPARE(reviewer.value("permission").toObject().value("task").toString(),QString("deny"));
    }
    void preserveOtherSettingsAndRemoveDeselected(){
        QTemporaryDir tmp;auto c=Project::defaultConfig();
        c.agents={"orchestrator","code-reviewer"};
        c.models={{"orchestrator","local/main"},{"code-reviewer","local/review"}};
        QString err;QVERIFY2(Project::save(tmp.path(),c,err),qPrintable(err));
        QFile f(tmp.filePath("opencode.json"));QVERIFY(f.open(QIODevice::ReadOnly));
        auto root=QJsonDocument::fromJson(f.readAll()).object();f.close();
        root.insert("custom_flag",42);
        QVERIFY(f.open(QIODevice::WriteOnly|QIODevice::Truncate));
        f.write(QJsonDocument(root).toJson());f.close();
        c.agents={"orchestrator"};c.models.remove("code-reviewer");
        QVERIFY2(Project::save(tmp.path(),c,err),qPrintable(err));
        QVERIFY(!QFile::exists(tmp.filePath(".opencode/agents/code-reviewer.md")));
        QVERIFY(f.open(QIODevice::ReadOnly));root=QJsonDocument::fromJson(f.readAll()).object();
        QCOMPARE(root.value("custom_flag").toInt(),42);
        QVERIFY(!root.value("agent").toObject().contains("code-reviewer"));
    }
    void mixedProvidersDoNotInstallFilters(){
        QTemporaryDir tmp; QVERIFY(tmp.isValid());
        auto c=Project::defaultConfig();
        c.agents={"orchestrator","software-engineer","verification-engineer"};
        // Synthetic IDs: provider/model choices are not a provider allowlist.
        c.models={{"orchestrator","custom-cloud/main"},
                  {"software-engineer","my-local-endpoint/coder"},
                  {"verification-engineer","another-provider/review"}};
        QString err;
        for(int pass=0;pass<2;++pass){
            QVERIFY2(Project::save(tmp.path(),c,err),qPrintable(err));
            QFile f(tmp.filePath("opencode.json"));
            QVERIFY(f.open(QIODevice::ReadOnly));
            const auto doc=QJsonDocument::fromJson(f.readAll());
            QVERIFY(doc.isObject());
            const auto root=doc.object();
            QVERIFY(!root.contains("enabled_providers"));
            QVERIFY(!root.contains("disabled_providers"));
            // No provider block means no per-provider model whitelist/blacklist.
            QVERIFY(!root.contains("provider"));
            const auto agents=root.value("agent").toObject();
            for(const auto& role:c.agents)
                QCOMPARE(agents.value(role).toObject().value("model"),c.models.value(role));
            ProjectConfig loaded;
            QVERIFY2(Project::load(tmp.path(),loaded,err),qPrintable(err));
            c=loaded;
        }
    }
    void preserveProviderSettings_data(){
        QTest::addColumn<bool>("explicitFilters");
        QTest::newRow("unrelated-provider-settings")<<false;
        QTest::newRow("explicit-user-filters")<<true;
    }
    void preserveProviderSettings(){
        QFETCH(bool,explicitFilters);
        QTemporaryDir tmp; QVERIFY(tmp.isValid());
        QJsonObject providerSettings{
            {"custom-cloud",QJsonObject{
                {"name","User endpoint"},
                {"options",QJsonObject{{"baseURL","https://example.invalid/v1"},{"timeout",12345}}},
                {"models",QJsonObject{{"main",QJsonObject{{"name","User model"}}}}}}},
            {"unused-provider",QJsonObject{{"name","Keep even when not selected"}}}};
        if(explicitFilters){
            auto provider=providerSettings.value("custom-cloud").toObject();
            provider.insert("whitelist",QJsonArray{"main","other-model"});
            provider.insert("blacklist",QJsonArray{"blocked-model"});
            providerSettings.insert("custom-cloud",provider);
        }
        QJsonObject original{{"provider",providerSettings},{"custom_flag",42}};
        if(explicitFilters){
            original.insert("enabled_providers",QJsonArray{"custom-cloud","unused-provider"});
            original.insert("disabled_providers",QJsonArray{"deliberately-disabled"});
        }
        QFile f(tmp.filePath("opencode.json"));
        QVERIFY(f.open(QIODevice::WriteOnly));
        const auto bytes=QJsonDocument(original).toJson();
        QCOMPARE(f.write(bytes),qint64(bytes.size()));
        f.close();
        auto c=Project::defaultConfig();
        c.agents={"orchestrator","software-engineer"};
        c.models={{"orchestrator","custom-cloud/main"},{"software-engineer","my-local-endpoint/coder"}};
        QString err;
        for(int pass=0;pass<2;++pass){
            QVERIFY2(Project::save(tmp.path(),c,err),qPrintable(err));
            QVERIFY(f.open(QIODevice::ReadOnly));
            const auto doc=QJsonDocument::fromJson(f.readAll());
            f.close();
            QVERIFY(doc.isObject());
            const auto root=doc.object();
            QCOMPARE(root.value("provider"),original.value("provider"));
            QCOMPARE(root.value("custom_flag"),original.value("custom_flag"));
            for(const auto& key:{"enabled_providers","disabled_providers"}){
                QCOMPARE(root.contains(key),original.contains(key));
                QCOMPARE(root.value(key),original.value(key));
            }
        }
    }
    void rejectIncompleteConfig(){
        QTemporaryDir tmp;auto c=Project::defaultConfig();
        QString err;QVERIFY(!Project::save(tmp.path(),c,err));
        QVERIFY(!QFile::exists(tmp.filePath("opencode.json")));
    }
    void rejectSymlinkOutsideProject(){
        QTemporaryDir tmp;QTemporaryDir other;QVERIFY(tmp.isValid());QVERIFY(other.isValid());
        if(!QFile::link(other.path(),tmp.filePath(".opencode"))) QSKIP("Symlink creation not permitted on this runner");
        auto c=Project::defaultConfig();c.models.insert("orchestrator","local/test");
        QString err;QVERIFY(!Project::save(tmp.path(),c,err));
        QVERIFY(!QFile::exists(other.filePath("agents/orchestrator.md")));
    }
    void secretsProtectedAfterReadOverride(){
        QTemporaryDir tmp;auto c=Project::defaultConfig();
        c.agents={"orchestrator","software-engineer"};
        c.models={{"orchestrator","local/main"},{"software-engineer","local/coder"}};
        c.policy.insert("agent_overrides",QJsonObject{{"software-engineer",QJsonObject{{"read","allow"}}}});
        QString err;const auto root=Project::openCodeConfig(tmp.path(),c,err);
        QVERIFY2(err.isEmpty(),qPrintable(err));
        const auto p=root.value("agent").toObject().value("software-engineer").toObject().value("permission").toObject();
        const auto read=p.value("read").toObject();
        QCOMPARE(read.value("*.env").toString(),QString("ask"));
        QCOMPARE(read.value("*.env.*").toString(),QString("ask"));
    }
    void reviewerReadOnly(){
        QTemporaryDir tmp;auto c=Project::defaultConfig();
        c.agents={"orchestrator","code-reviewer"};
        c.models={{"orchestrator","local/main"},{"code-reviewer","local/review"}};
        c.policy.insert("agent_overrides",QJsonObject{{"code-reviewer",QJsonObject{{"bash","allow"},{"edit","allow"}}}});
        QString err;auto root=Project::openCodeConfig(tmp.path(),c,err);QVERIFY2(err.isEmpty(),qPrintable(err));
        auto p=root.value("agent").toObject().value("code-reviewer").toObject().value("permission").toObject();
        QCOMPARE(p.value("bash").toString(),QString("deny"));
        QCOMPARE(p.value("edit").toString(),QString("deny"));
    }
};
QTEST_GUILESS_MAIN(ProjectTests)
#include "ProjectTests.moc"
