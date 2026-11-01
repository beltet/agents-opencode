#include "MainWindow.h"
#include <QCheckBox>
#include <QComboBox>
#include <QDesktopServices>
#include <QDir>
#include <QFileDialog>
#include <QFormLayout>
#include <QGroupBox>
#include <QHeaderView>
#include <QHBoxLayout>
#include <QLabel>
#include <QLineEdit>
#include <QMessageBox>
#include <QPlainTextEdit>
#include <QProcess>
#include <QPushButton>
#include <QScrollArea>
#include <QSplitter>
#include <QTableWidget>
#include <QTabWidget>
#include <QVBoxLayout>
#include <QUrl>
#include <QJsonArray>
#include <QJsonObject>
#include <QJsonDocument>
#include <QRegularExpression>
#include <QStyle>
#include <QApplication>
#include <QSignalBlocker>

namespace {
QComboBox* choice(const QStringList& options, const QString& initial, QWidget* parent) {
    auto* c=new QComboBox(parent);
    c->addItems(options);
    int index=c->findText(initial);
    c->setCurrentIndex(index>=0?index:0);
    return c;
}
QComboBox* permission(QWidget* parent,const QString& initial="ask"){
    auto* c=choice({"deny","ask","allow"},initial,parent);
    c->setItemText(0,"Neka");c->setItemText(1,"Fråga");c->setItemText(2,"Tillåt");
    return c;
}
QString permissionValue(QComboBox* box){return QStringList{"deny","ask","allow"}.value(box->currentIndex(),"ask");}
void setPermission(QComboBox* box,const QString& value) {
    const int i=QStringList{"deny","ask","allow"}.indexOf(value);
    box->setCurrentIndex(i>=0?i:1);
}
QGroupBox* group(const QString& name,QVBoxLayout* parent){
    auto* b=new QGroupBox(name);b->setLayout(new QVBoxLayout);parent->addWidget(b);return b;
}
QString lines(const QJsonObject& object,const QString& key){
    QStringList result;
    for(auto x:object.value(key).toArray()) if(x.isString())result<<x.toString();
    return result.join('\n');
}
QJsonArray toLines(QPlainTextEdit* field){
    QJsonArray values;
    for(auto line:field->toPlainText().split('\n')){
        line=line.trimmed();if(!line.isEmpty())values.append(line);
    }
    return values;
}
QString safeError(QProcess& p){return QString::fromUtf8(p.readAllStandardError()).trimmed();}
QString safeOutput(QProcess& p){return QString::fromUtf8(p.readAllStandardOutput()).trimmed();}
}

MainWindow::MainWindow(QWidget* parent):QMainWindow(parent){
    resize(1030,760);
    setWindowTitle("Agents OpenCode — konfigurera agentteam");
    auto* content=new QWidget(this);
    auto* shell=new QVBoxLayout(content);
    shell->setContentsMargins(16,14,16,10);
    auto* title=new QLabel("Agents OpenCode",content);
    auto titlefont=title->font();titlefont.setPointSize(19);titlefont.setBold(true);title->setFont(titlefont);
    shell->addWidget(title);
    auto* subtitle=new QLabel("Välj projekt, experter och modeller manuellt. Orkestreraren anpassar arbetsfördelningen.",content);
    subtitle->setStyleSheet("color: palette(mid);");shell->addWidget(subtitle);
    auto* toolbar=new QHBoxLayout;
    path_=new QLineEdit(content);path_->setPlaceholderText("Projektmapp …");
    auto* browse=new QPushButton("Välj mapp…",content);
    auto* open=new QPushButton("Öppna projekt",content);
    toolbar->addWidget(new QLabel("Projekt:",content));toolbar->addWidget(path_,1);
    toolbar->addWidget(browse);toolbar->addWidget(open);
    shell->addLayout(toolbar);
    tabs_=new QTabWidget(content);
    tabs_->addTab(makeProjectTab(),"Projekt");
    tabs_->addTab(makeAgentsTab(),"Agenter och modeller");
    tabs_->addTab(makePermissionsTab(),"Behörigheter");
    tabs_->addTab(makeGitTab(),"Git / SSH");
    tabs_->addTab(makePreviewTab(),"Förhandsgranska");
    shell->addWidget(tabs_,1);
    auto* footer=new QHBoxLayout;
    status_=new QLabel("Välj en projektmapp för att börja.",content);
    status_->setWordWrap(true);
    auto* preview=new QPushButton("Visa ändringar",content);
    auto* save=new QPushButton("Spara och installera agentteam",content);
    save->setDefault(true);
    footer->addWidget(status_,1);footer->addWidget(preview);footer->addWidget(save);
    shell->addLayout(footer);
    setCentralWidget(content);
    connect(browse,&QPushButton::clicked,this,[this]{chooseFolder();});
    connect(open,&QPushButton::clicked,this,[this]{openProject();});
    connect(path_,&QLineEdit::returnPressed,this,[this]{openProject();});
    connect(preview,&QPushButton::clicked,this,[this]{previewChanges();});
    connect(save,&QPushButton::clicked,this,[this]{saveProject();});
    path_->setText(QDir::currentPath());
    openProject();
}

QWidget* MainWindow::makeProjectTab(){
    auto* page=new QWidget;
    auto* l=new QVBoxLayout(page);
    auto* hint=new QLabel("Beskriv vad som ska byggas. Installationsprogrammet analyserar inte projektet — orkestreraren läser beskrivningen.");
    hint->setWordWrap(true);l->addWidget(hint);
    brief_=new QPlainTextEdit(page);brief_->setPlaceholderText("Syfte, önskade funktioner, teknik, begränsningar, acceptanskriterier …");
    l->addWidget(brief_,1);
    auto* inf=new QLabel("Sparas i PROJECT_BRIEF.md. Befintliga projektfiler skrivs inte om förutom uttryckligen hanterade konfigurationsfiler.",page);
    inf->setWordWrap(true);inf->setStyleSheet("color: palette(mid);");l->addWidget(inf);
    return page;
}

QWidget* MainWindow::makeAgentsTab(){
    auto* page=new QWidget;
    auto* l=new QVBoxLayout(page);
    auto* header=new QHBoxLayout;
    auto* fetch=new QPushButton("Hämta modeller från OpenCode",page);
    allModel_=new QLineEdit(page);allModel_->setPlaceholderText("provider/model för alla markerade");
    auto* assign=new QPushButton("Tilldela alla",page);
    header->addWidget(fetch);header->addStretch(1);header->addWidget(allModel_,1);header->addWidget(assign);
    l->addLayout(header);
    auto* table=new QTableWidget(page);
    table->setObjectName("agentTable");
    table->setColumnCount(3);
    table->setHorizontalHeaderLabels({"Aktiv", "Specialist", "Modell (manuellt val)"});
    auto roles=Project::availableRoles();roles.sort();roles.removeAll("orchestrator");roles.prepend("orchestrator");
    table->setRowCount(roles.size());
    table->verticalHeader()->hide();
    table->setSelectionMode(QAbstractItemView::NoSelection);
    table->setEditTriggers(QAbstractItemView::NoEditTriggers);
    table->horizontalHeader()->setSectionResizeMode(0,QHeaderView::ResizeToContents);
    table->horizontalHeader()->setSectionResizeMode(1,QHeaderView::Stretch);
    table->horizontalHeader()->setSectionResizeMode(2,QHeaderView::Stretch);
    for(int i=0;i<roles.size();++i){
        const auto& r=roles[i];
        auto* toggle=new QCheckBox(table);toggle->setChecked(r=="orchestrator");
        auto* cell=new QWidget(table);auto* cl=new QHBoxLayout(cell);cl->setContentsMargins(8,0,4,0);cl->addWidget(toggle);cl->addStretch();
        table->setCellWidget(i,0,cell);
        auto* item=new QTableWidgetItem(r=="orchestrator"?"orchestrator (krävs)":r);
        table->setItem(i,1,item);
        auto* model=new QComboBox(table);model->setEditable(true);
        model->setInsertPolicy(QComboBox::NoInsert);model->setMinimumContentsLength(24);
        model->setPlaceholderText("Välj eller skriv provider/model");
        model->lineEdit()->setPlaceholderText("provider/model");
        table->setCellWidget(i,2,model);
        agents_.insert(r,{toggle,model});
        if(r=="orchestrator")toggle->setEnabled(false);
    }
    table->verticalHeader()->setDefaultSectionSize(34);
    l->addWidget(table,1);
    auto* note=new QLabel("Alla modellval görs av dig. Inga agenter aktiveras automatiskt. Saknas OpenCode eller modeller, skriv modell-ID själv.",page);
    note->setWordWrap(true);note->setStyleSheet("color: palette(mid);");l->addWidget(note);
    connect(fetch,&QPushButton::clicked,this,[this]{loadModels();});
    connect(assign,&QPushButton::clicked,this,[this]{applyBulkModel();});
    return page;
}

QWidget* MainWindow::makePermissionsTab(){
    auto* page=new QWidget;auto* layout=new QVBoxLayout(page);
    auto* scroller=new QScrollArea(page);scroller->setWidgetResizable(true);scroller->setFrameShape(QFrame::NoFrame);
    auto* interior=new QWidget(scroller);auto* l=new QVBoxLayout(interior);
    auto* summary=new QLabel("Välj grundbehörigheter. Regler för URL:er, USB och firmware dokumenteras i policyn men är inte en fullständig OS-sandbox.",interior);
    summary->setWordWrap(true);l->addWidget(summary);
    auto* base=group("OpenCode-verktyg",l);auto* form=new QFormLayout;
    read_=permission(base,"allow");edit_=permission(base);bash_=permission(base);external_=permission(base,"deny");internet_=permission(base);
    form->addRow("Läsa filer",read_);form->addRow("Redigera filer",edit_);form->addRow("Köra kommandon",bash_);
    form->addRow("Utanför projektmappen",external_);form->addRow("Internet och webbsökning",internet_);
    static_cast<QVBoxLayout*>(base->layout())->addLayout(form);
    auto* net=group("Nätverk (avsiktsregler)",l);auto* nf=new QFormLayout;
    networkAllow_=new QPlainTextEdit(net);networkDeny_=new QPlainTextEdit(net);
    for(auto* f:{networkAllow_,networkDeny_})f->setFixedHeight(68);
    nf->addRow("Tillåtna adresser, en per rad",networkAllow_);nf->addRow("Blockerade adresser, en per rad",networkDeny_);
    static_cast<QVBoxLayout*>(net->layout())->addLayout(nf);
    auto* fs=group("Lokala sökvägar och nätverksdiskar (avsiktsregler)",l);auto* pf=new QFormLayout;
    paths_=new QPlainTextEdit(fs);pathsDeny_=new QPlainTextEdit(fs);
    shares_=new QPlainTextEdit(fs);sharesDeny_=new QPlainTextEdit(fs);
    for(auto* f:{paths_,pathsDeny_,shares_,sharesDeny_})f->setFixedHeight(54);
    pf->addRow("Tillåtna sökvägar (en per rad)",paths_);
    pf->addRow("Blockerade sökvägar (en per rad)",pathsDeny_);
    pf->addRow("Tillåtna monteringar/UNC",shares_);
    pf->addRow("Blockerade monteringar/UNC",sharesDeny_);
    static_cast<QVBoxLayout*>(fs->layout())->addLayout(pf);
    auto* hardware=group("USB och firmware",l);auto* hf=new QFormLayout;
    usb_=permission(hardware,"deny");firmware_=permission(hardware,"deny");devices_=new QPlainTextEdit(hardware);devices_->setFixedHeight(60);
    hf->addRow("USB-styrning",usb_);hf->addRow("Firmwareflashning",firmware_);hf->addRow("Tillåtna enheter (VID/PID, serienr)",devices_);
    static_cast<QVBoxLayout*>(hardware->layout())->addLayout(hf);
    auto* git=group("Git-behörigheter",l);auto* gf=new QFormLayout;
    gitCommit_=permission(git);gitPush_=permission(git,"deny");gitForce_=permission(git,"deny");
    gf->addRow("Commit",gitCommit_);gf->addRow("Push",gitPush_);gf->addRow("Force push",gitForce_);
    static_cast<QVBoxLayout*>(git->layout())->addLayout(gf);
    unattended_=new QCheckBox("Förbered obevakat läge (starta OpenCode med --auto; granska säkerhetsreglerna först)",interior);
    l->addWidget(unattended_);
    auto* byAgent=group("Undantag per agent",l);
    auto* af=new QFormLayout;
    overrideRole_=new QComboBox(byAgent);overrideRole_->addItems(Project::availableRoles());
    auto inherit=[&](QComboBox*& c){c=choice({"inherit","deny","ask","allow"},"inherit",byAgent);c->setItemText(0,"Ärv från projekt");c->setItemText(1,"Neka");c->setItemText(2,"Fråga");c->setItemText(3,"Tillåt");};
    inherit(overrideRead_);inherit(overrideEdit_);inherit(overrideBash_);inherit(overrideWeb_);
    af->addRow("Agent",overrideRole_);af->addRow("Läsning",overrideRead_);
    af->addRow("Redigering",overrideEdit_);af->addRow("Kommandon",overrideBash_);af->addRow("Webbhämtning",overrideWeb_);
    static_cast<QVBoxLayout*>(byAgent->layout())->addLayout(af);
    auto* agentWarning=new QLabel("Kodgranskare och andra skrivskyddade roller kan inte få redigerings- eller shellbehörighet genom dessa undantag.",byAgent);
    agentWarning->setWordWrap(true);byAgent->layout()->addWidget(agentWarning);
    connect(overrideRole_,&QComboBox::currentTextChanged,this,[this](const QString&){loadOverride();});
    for(auto* combo:{overrideRead_,overrideEdit_,overrideBash_,overrideWeb_})
        connect(combo,QOverload<int>::of(&QComboBox::currentIndexChanged),this,[this](int){saveOverride();});
    l->addStretch();scroller->setWidget(interior);layout->addWidget(scroller);
    return page;
}

QWidget* MainWindow::makeGitTab(){
    auto* page=new QWidget;auto* l=new QVBoxLayout(page);
    auto* form=new QFormLayout;
    gitMode_=choice({"local","existing","remote"},"local",page);
    gitMode_->setItemText(0,"Enbart lokalt Git");gitMode_->setItemText(1,"Befintligt Git (ändra inte remote)");gitMode_->setItemText(2,"Remote via SSH/HTTPS");
    remote_=new QLineEdit(page);remote_->setText("origin");
    host_=new QLineEdit(page);host_->setPlaceholderText("git.example.org");
    port_=new QLineEdit(page);port_->setText("22");
    sshUser_=new QLineEdit(page);sshUser_->setText("git");
    sshKey_=new QLineEdit(page);sshKey_->setPlaceholderText("Valfritt: sökväg till befintlig SSH-nyckel");
    repo_=new QLineEdit(page);repo_->setPlaceholderText("team/project.git eller fullständig URL");
    author_=new QLineEdit(page);email_=new QLineEdit(page);
    branch_=new QLineEdit(page);branch_->setText("main");
    form->addRow("Repository-läge",gitMode_);
    form->addRow("Remote-namn",remote_);
    form->addRow("Git-server (SSH)",host_);
    form->addRow("SSH-port",port_);
    form->addRow("SSH-användare",sshUser_);
    auto* keyBox=new QWidget(page);auto* kl=new QHBoxLayout(keyBox);kl->setContentsMargins(0,0,0,0);
    auto* keyBrowse=new QPushButton("Välj…",keyBox);kl->addWidget(sshKey_,1);kl->addWidget(keyBrowse);
    form->addRow("SSH-identitet (endast referens)",keyBox);
    connect(keyBrowse,&QPushButton::clicked,this,[this]{
        auto name=QFileDialog::getOpenFileName(this,"Välj befintlig SSH-identitetsfil",QDir::homePath()+"/.ssh");
        if(!name.isEmpty())sshKey_->setText(name);
    });
    form->addRow("Repository-sökväg eller HTTPS/SSH URL",repo_);
    form->addRow("Commit-författare",author_);
    form->addRow("Commit-email",email_);
    form->addRow("Gren (referens)",branch_);
    l->addLayout(form);
    auto* info=new QLabel("Att spara teamet skriver bara avsedda Git-inställningar till projektkonfigurationen. Knappen nedan gör verkliga lokala Git-ändringar efter bekräftelse. Den pushar aldrig.",page);
    info->setWordWrap(true);l->addWidget(info);
    auto* buttons=new QHBoxLayout;
    auto* check=new QPushButton("Kontrollera lokal Git",page);
    auto* apply=new QPushButton("Tillämpa Git-inställningar…",page);
    buttons->addWidget(check);buttons->addWidget(apply);buttons->addStretch();l->addLayout(buttons);l->addStretch();
    connect(check,&QPushButton::clicked,this,[this]{gitCheck();});
    connect(apply,&QPushButton::clicked,this,[this]{gitApply();});
    return page;
}

QWidget* MainWindow::makePreviewTab(){
    auto* page=new QWidget;auto* l=new QVBoxLayout(page);
    auto* hint=new QLabel("Förhandsgranskningen visar genererad OpenCode-konfiguration. Befintliga hanterade filer säkerhetskopieras innan de ändras.",page);
    hint->setWordWrap(true);l->addWidget(hint);
    preview_=new QPlainTextEdit(page);preview_->setReadOnly(true);
    QFont font=preview_->font();font.setFamily("monospace");preview_->setFont(font);
    l->addWidget(preview_,1);
    return page;
}

void MainWindow::setStatus(const QString& msg,bool bad){
    status_->setText(msg);
    status_->setStyleSheet(bad?"color:#bd3535;font-weight:600":"color:palette(text)");
}
void MainWindow::chooseFolder(){
    auto dir=QFileDialog::getExistingDirectory(this,"Välj projektmapp",path_->text());
    if(!dir.isEmpty()){path_->setText(dir);openProject();}
}
void MainWindow::openProject(){
    const QString path=QDir(path_->text().trimmed()).absolutePath();
    if(!QDir(path).exists()){setStatus("Projektmappen finns inte. Skapa den först.",true);return;}
    ProjectConfig c;QString error;
    if(!Project::load(path,c,error)){
        QMessageBox::warning(this,"Kunde inte läsa projekt",error);
        setStatus(error,true);return;
    }
    root_=path;path_->setText(root_);current_=c;showConfig();
    setStatus("Projekt öppnat: "+root_);
}
void MainWindow::showConfig(){
    brief_->setPlainText(current_.brief);
    for(auto it=agents_.begin();it!=agents_.end();++it){
        it->enabled->setChecked(it.key()=="orchestrator" || current_.agents.contains(it.key()));
        it->model->setEditText(current_.models.value(it.key()).toString());
    }
    localOverrides_=current_.policy.value("agent_overrides").toObject();
    if(overrideRole_){overrideRole_->setCurrentIndex(0);loadOverride();}
    auto tools=current_.policy.value("tools").toObject();
    auto git=current_.policy.value("git").toObject();
    auto net=current_.policy.value("network").toObject();
    setPermission(read_,tools.value("read").toString("allow"));
    setPermission(edit_,tools.value("edit").toString("ask"));
    setPermission(bash_,tools.value("bash").toString("ask"));
    setPermission(external_,tools.value("external_directory").toString("deny"));
    setPermission(internet_,net.value("internet").toString("ask"));
    networkAllow_->setPlainText(lines(net,"allow"));networkDeny_->setPlainText(lines(net,"deny"));
    QStringList pathLines,pathDenyLines,shareLines,shareDenyLines,devLines;
    for(const auto& v:current_.policy.value("paths").toArray())pathLines<<v.toString();
    for(const auto& v:current_.policy.value("paths_deny").toArray())pathDenyLines<<v.toString();
    for(const auto& v:current_.policy.value("shares").toArray())shareLines<<v.toString();
    for(const auto& v:current_.policy.value("shares_deny").toArray())shareDenyLines<<v.toString();
    for(const auto& v:current_.policy.value("devices").toArray())devLines<<v.toString();
    paths_->setPlainText(pathLines.join('\n'));
    pathsDeny_->setPlainText(pathDenyLines.join('\n'));
    shares_->setPlainText(shareLines.join('\n'));
    sharesDeny_->setPlainText(shareDenyLines.join('\n'));
    devices_->setPlainText(devLines.join('\n'));
    auto hw=current_.policy.value("hardware").toObject();
    setPermission(usb_,hw.value("usb").toString("deny"));setPermission(firmware_,hw.value("firmware").toString("deny"));
    setPermission(gitCommit_,git.value("commit").toString("ask"));
    setPermission(gitPush_,git.value("push").toString("deny"));
    setPermission(gitForce_,git.value("force_push").toString("deny"));
    unattended_->setChecked(current_.policy.value("unattended").toBool(false));
    const auto g=current_.git;
    gitMode_->setCurrentIndex(qMax(0,QStringList{"local","existing","remote"}.indexOf(g.value("mode").toString("local"))));
    remote_->setText(g.value("remote").toString("origin"));host_->setText(g.value("host").toString());
    port_->setText(QString::number(g.value("ssh_port").toInt(22)));sshUser_->setText(g.value("ssh_user").toString("git"));
    repo_->setText(g.value("repo").toString());sshKey_->setText(g.value("ssh_identity").toString());
    author_->setText(g.value("author").toString());
    email_->setText(g.value("email").toString());branch_->setText(g.value("branch").toString("main"));
    preview_->clear();
}

bool MainWindow::collect(ProjectConfig& c){
    if(root_.isEmpty()){setStatus("Öppna en projektmapp först.",true);return false;}
    c=current_;
    c.agents.clear();c.models=QJsonObject{};
    for(auto it=agents_.begin();it!=agents_.end();++it){
        if(it->enabled->isChecked()){
            c.agents.append(it.key());
            auto model=it->model->currentText().trimmed();
            if(model.isEmpty()){
                tabs_->setCurrentIndex(1);
                QMessageBox::warning(this,"Modell saknas","Välj modell för agenten: "+it.key());
                return false;
            }
            c.models.insert(it.key(),model);
        }
    }
    c.brief=brief_->toPlainText();
    auto tools=c.policy.value("tools").toObject();
    tools.insert("read",permissionValue(read_));tools.insert("edit",permissionValue(edit_));
    tools.insert("bash",permissionValue(bash_));tools.insert("external_directory",permissionValue(external_));
    c.policy.insert("tools",tools);
    auto net=c.policy.value("network").toObject();
    net.insert("internet",permissionValue(internet_));net.insert("allow",toLines(networkAllow_));net.insert("deny",toLines(networkDeny_));
    c.policy.insert("network",net);
    c.policy.insert("paths",toLines(paths_));c.policy.insert("paths_deny",toLines(pathsDeny_));
    c.policy.insert("shares",toLines(shares_));c.policy.insert("shares_deny",toLines(sharesDeny_));
    c.policy.insert("devices",toLines(devices_));
    c.policy.insert("hardware",QJsonObject{{"usb",permissionValue(usb_)},{"firmware",permissionValue(firmware_)}});
    auto git=c.policy.value("git").toObject();
    git.insert("commit",permissionValue(gitCommit_));git.insert("push",permissionValue(gitPush_));git.insert("force_push",permissionValue(gitForce_));
    c.policy.insert("git",git);
    c.policy.insert("unattended",unattended_->isChecked());
    c.policy.insert("agent_overrides",localOverrides_);
    c.git=QJsonObject{{"mode",QStringList{"local","existing","remote"}.value(gitMode_->currentIndex())},
        {"remote",remote_->text().trimmed()}, {"host",host_->text().trimmed()},
        {"ssh_port",port_->text().toInt()}, {"ssh_user",sshUser_->text().trimmed()},
        {"ssh_identity",sshKey_->text().trimmed()},
        {"repo",repo_->text().trimmed()}, {"author",author_->text().trimmed()},
        {"email",email_->text().trimmed()}, {"branch",branch_->text().trimmed()}};
    return true;
}
void MainWindow::previewChanges(){
    ProjectConfig c;if(!collect(c))return;
    QString error;auto p=Project::preview(root_,c,error);
    if(!error.isEmpty()){QMessageBox::warning(this,"Konfigurationsfel",error);setStatus(error,true);return;}
    preview_->setPlainText(p);tabs_->setCurrentIndex(4);
    setStatus("Förhandsgranskning klar. Inga filer har ändrats.");
}
void MainWindow::saveProject(){
    // Avoid emitting V1 configuration for a known V2 OpenCode runtime.
    QProcess version;
    version.start("opencode",{"--version"});
    if(version.waitForStarted(1000)){
        if(version.waitForFinished(3000)){
            const auto output=QString::fromUtf8(version.readAllStandardOutput())+QString::fromUtf8(version.readAllStandardError());
            const auto match=QRegularExpression("(?:^|[^0-9])([0-9]+)\\.[0-9]+\\.[0-9]+").match(output);
            if(match.hasMatch() && match.captured(1).toInt()>=2){
                QMessageBox::warning(this,"OpenCode 2.x","Den här versionen genererar konfiguration för OpenCode 1.x.\nOpenCode 2.x har ett annat behörighetsschema. Ingen installation har utförts.");
                return;
            }
        }else {version.kill();version.waitForFinished();}
    }
    ProjectConfig c;if(!collect(c))return;
    QString error;auto p=Project::preview(root_,c,error);
    if(!error.isEmpty()){QMessageBox::warning(this,"Konfigurationsfel",error);setStatus(error,true);return;}
    if(QMessageBox::question(this,"Spara projektteam",
       "Skapa/uppdatera agentfiler i:\n"+root_+"\n\nBefintliga hanterade filer säkerhetskopieras innan ändring. Fortsätta?",
       QMessageBox::Yes|QMessageBox::No,QMessageBox::No)!=QMessageBox::Yes)return;
    if(!Project::save(root_,c,error)){
        QMessageBox::critical(this,"Kunde inte spara",error);setStatus(error,true);return;
    }
    current_=c;preview_->setPlainText(p);
    setStatus("Agentteamet har sparats i projektet. Git ändras separat.");
    QMessageBox::information(this,"Klart","Agentteamet har installerats i projektmappen.\n\nStarta OpenCode där när du vill använda agenterna.");
}
void MainWindow::loadModels(){
    QProcess proc;
    proc.start("opencode",{"models"});
    if(!proc.waitForStarted(2500)){
        QMessageBox::information(this,"OpenCode saknas","Kunde inte köra 'opencode models'. Du kan ändå skriva modell-ID manuellt.");return;
    }
    if(!proc.waitForFinished(12000)){
        proc.kill();proc.waitForFinished();
        QMessageBox::warning(this,"Timeout","OpenCode svarade inte i tid. Du kan ange modeller manuellt.");return;
    }
    if(proc.exitCode()!=0){
        QMessageBox::warning(this,"Modellhämtning misslyckades",safeError(proc));return;
    }
    QStringList found;
    for(const auto& raw: safeOutput(proc).split('\n')){
        auto name=raw.trimmed();
        if(name.contains('/') && !name.contains(' ') && !found.contains(name))found<<name;
    }
    if(found.isEmpty()){QMessageBox::information(this,"Inga modeller","Inga användbara modell-ID:n hittades. Skriv manuellt.");return;}
    found.sort();availableModels_=found;
    for(auto it=agents_.begin();it!=agents_.end();++it){
        auto value=it->model->currentText();
        it->model->clear();it->model->addItems(found);it->model->setEditText(value);
    }
    setStatus(QString::number(found.size())+" modell-ID:n hittades. Inga modeller har valts automatiskt.");
}
void MainWindow::applyBulkModel(){
    auto m=allModel_->text().trimmed();if(m.isEmpty()){setStatus("Skriv ett modell-ID först.",true);return;}
    int n=0;for(auto it=agents_.begin();it!=agents_.end();++it)if(it->enabled->isChecked()){
        it->model->setEditText(m);++n;
    }
    setStatus(QString::number(n)+" markerade agenter har tilldelats modellen. Spara för att installera.");
}
void MainWindow::gitCheck(){
    if(root_.isEmpty())return;
    QProcess proc;proc.start("git",{"-C",root_,"status","--short","--branch"});
    if(!proc.waitForFinished(5000)){
        proc.kill();proc.waitForFinished();
        QMessageBox::warning(this,"Git","Git svarade inte i tid.");return;
    }
    auto out=safeOutput(proc);if(proc.exitCode()!=0)out=safeError(proc);
    QMessageBox::information(this,"Git-status",out.isEmpty()?"Inga ändringar.":out);
}
void MainWindow::loadOverride(){
    if(!overrideRole_)return;
    const auto obj=localOverrides_.value(overrideRole_->currentText()).toObject();
    const QStringList keys={"read","edit","bash","webfetch"};
    const QList<QComboBox*> combos={overrideRead_,overrideEdit_,overrideBash_,overrideWeb_};
    for(int i=0;i<keys.size();++i){
        const QSignalBlocker guard(combos[i]);
        const auto value=obj.value(keys[i]).toString("inherit");
        int idx=QStringList{"inherit","deny","ask","allow"}.indexOf(value);
        combos[i]->setCurrentIndex(qMax(0,idx));
    }
}
void MainWindow::saveOverride(){
    if(!overrideRole_)return;
    const auto name=overrideRole_->currentText();
    QJsonObject obj=localOverrides_.value(name).toObject();
    const QStringList keys={"read","edit","bash","webfetch"};
    const QList<QComboBox*> combos={overrideRead_,overrideEdit_,overrideBash_,overrideWeb_};
    for(int i=0;i<keys.size();++i){
        const QString value=QStringList{"inherit","deny","ask","allow"}.value(combos[i]->currentIndex(),"inherit");
        if(value=="inherit")obj.remove(keys[i]);else obj.insert(keys[i],value);
    }
    if(obj.isEmpty())localOverrides_.remove(name);else localOverrides_.insert(name,obj);
}
void MainWindow::gitApply(){
    ProjectConfig c;if(!collect(c))return;
    QString url;
    const auto git=c.git;const QString mode=git.value("mode").toString();
    if(mode=="remote"){
        auto host=git.value("host").toString(),repo=git.value("repo").toString();
        const int port=git.value("ssh_port").toInt();
        if(repo.startsWith("https://")||repo.startsWith("ssh://"))url=repo;
        else if(host.isEmpty()||repo.isEmpty()||port<1||port>65535){
            QMessageBox::warning(this,"Ogiltig remote","Ange värd, repository och SSH-port 1–65535.");return;
        } else {
            QString user=git.value("ssh_user").toString();if(user.isEmpty())user="git";
            if(!QRegularExpression("^[a-zA-Z0-9._-]+$").match(user).hasMatch() ||
               !QRegularExpression("^[a-zA-Z0-9.:-]+$").match(host).hasMatch() ||
               repo.contains("..") || repo.startsWith('/') || repo.contains(' ')){
                QMessageBox::warning(this,"Ogiltig remote","Felaktigt användarnamn, server eller repository-sökväg.");return;
            }
            url=QString("ssh://%1@%2:%3/%4").arg(user,host,QString::number(port),repo);
        }
    }
    const auto author=git.value("author").toString(),email=git.value("email").toString(),remote=git.value("remote").toString("origin");
    if(mode=="remote"&&!QRegularExpression("^[A-Za-z0-9._-]+$").match(remote).hasMatch()){
        QMessageBox::warning(this,"Ogiltig remote","Ange ett enkelt remote-namn.");return;
    }
    QString changes="Projekt: "+root_+"\n";
    changes+="Git-läge: "+mode+"\n";
    if(!author.isEmpty())changes+="Author: "+author+"\n";
    if(!email.isEmpty())changes+="Email: "+email+"\n";
    if(!url.isEmpty())changes+="Ny remote "+remote+": "+url+"\n";
    changes+="\nBefintlig remote skrivs aldrig över. Inga push-kommandon körs.";
    if(QMessageBox::question(this,"Bekräfta Git-ändringar",changes,QMessageBox::Yes|QMessageBox::No,QMessageBox::No)!=QMessageBox::Yes)return;
    auto run=[&](const QStringList& args,QString& out){
        QProcess p;p.start("git",QStringList{"-C",root_}+args);
        if(!p.waitForFinished(6000)){p.kill();p.waitForFinished();out="Git timeout";return false;}
        out=safeError(p);return p.exitCode()==0 && p.exitStatus()==QProcess::NormalExit;
    };
    QString error;
    if(mode=="local"){
        if(!run({"rev-parse","--show-toplevel"},error) && !run({"init"},error)){
            QMessageBox::warning(this,"Git init",error);return;
        }
    } else if(!run({"rev-parse","--show-toplevel"},error)){
        QMessageBox::warning(this,"Git saknas","Projektet saknar lokalt Git-repository. Initiera Git separat eller välj lokalt läge.");return;
    }
    if(!author.isEmpty() && !run({"config","--local","user.name",author},error)){
        QMessageBox::warning(this,"Git author",error);return;
    }
    if(!email.isEmpty() && !run({"config","--local","user.email",email},error)){
        QMessageBox::warning(this,"Git email",error);return;
    }
    if(mode=="remote"){
        if(run({"remote","get-url",remote},error)){
            QMessageBox::information(this,"Git remote finns redan","Remote '"+remote+"' finns redan. Den har inte ändrats.");
        } else if(!run({"remote","add",remote,url},error)){
            QMessageBox::warning(this,"Git remote",error);return;
        }
    }
    setStatus("Lokala Git-inställningar tillämpade. Spara agentteam separat för att lagra dina val.");
    QMessageBox::information(this,"Git klart","Git-inställningar har tillämpats lokalt. Ingen push har gjorts.");
}
