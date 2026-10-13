# Lernplattform bearbeiten

`Startseite bearbeiten.cmd` doppelt anklicken. Der lokale Editor öffnet sich im Standardbrowser. Die Startdatei prüft den Dienst, startet ihn bei Bedarf und öffnet den Browser erst, wenn er erreichbar ist. Die Adresse alleine startet den Dienst nicht. Nach Neustart des Computers oder Ausschalten des Dienstes die Startdatei erneut doppelt anklicken. Danach erreichst du ihn unter http://127.0.0.1:8767/editor. Der Dienst ist ausschließlich auf diesem Computer erreichbar.

Texte direkt anklicken und ändern. Die Werkzeugleiste erlaubt das Einfügen von Texten, Überschriften und Bildern, Schriftgröße, Breite und Ausrichtung, Verschieben und Löschen sowie Rückgängig und Wiederholen. Die Pfeile verschieben das ausgewählte Element bzw. seinen Modulblock innerhalb desselben Bereichs; Modulblöcke lassen sich auch am Griff ziehen. Bilder dürfen PNG, JPG, GIF oder WebP sein (bis 10 MB).

Mit „Vorschau“ siehst du deine aktuellen Änderungen ohne Bearbeitungshilfen. Mit „Speichern“ wird die gerade geöffnete Seite auf der Festplatte ersetzt: Startseite oder ausgewählte Modellseite. Vorher wird der bisherige Stand unter `sicherungen/` abgelegt. Neue Bilder landen in `assets/uploads/`. Ungespeicherte Änderungen bleiben nur im geöffneten Browser; beim Verlassen erscheint eine Warnung.

Die normale `index.html` enthält keine Editorwerkzeuge und bleibt unabhängig vom lokalen Dienst nutzbar. Es findet kein GitHub-Upload statt. Die Sicherungen enthalten frühere HTML-Stände; ihre relativen Bild- und Stylesheet-Pfade funktionieren erst nach Wiederherstellung im Projektordner.

Unter „Lokaler Dienst“ kann der Dienst mit „Lokalen Dienst ausschalten“ beendet werden; anschließend kannst du den Browser-Tab schließen. Bei ungespeicherten Änderungen verlangt der Editor zuerst Speichern oder Rückgängig. Der Editor ist eine lokale Autorenhilfe, kein Teilnehmer-Login oder öffentlicher Administrationsbereich.

Geprüft: Dateispeicherung mit Sicherung und Konflikterkennung sowie Textbearbeitung, Rückgängig/Wiederholen, Reihenfolge, Löschen/Wiederherstellen, Schriftgröße, Bildimport, Vorschau und bereinigte HTML-Ausgabe. Die Funktionsprüfung erfolgte in einer isolierten DOM- und Server-Testumgebung; die Glasl-Seite wurde zusätzlich im echten Browser geprüft (Bearbeiten, Rückgängig, Speichern, Vorschau und Abschnittssprünge).

Das Schließen des Browser-Tabs beendet den Dienst nicht. Fehlermeldungen des Dienstes stehen unter `.local/editor.log`. Die sichtbare Startdatei zeigt Startfehler an, statt still zu scheitern.

Der Starthelfer lässt Windows den Editor-Prozess unabhängig vom aufrufenden Programm erstellen. Dadurch hängt seine Laufzeit nicht an einem Chat-Werkzeugprozess. Der Dienst wird nicht beim Windows-Start automatisch gestartet; die Startdatei bleibt der Einstieg nach einem Neustart. Ausschalten erfordert eine zusätzliche Bestätigung.

Fettdruck: Text markieren und „Fett“ anklicken; erneut anklicken entfernt den Fettdruck der Markierung. Ohne Markierung wird das gesamte gewählte Textfeld formatiert. Die Auswahl bleibt beim Klicken auf die Werkzeugleiste erhalten.

Textfeldgröße: Textfeld anklicken und Breite sowie Feldhöhe einstellen oder am Eckgriff rechts unten ziehen. Die Feldhöhe ist eine Mindesthöhe: längere Inhalte bleiben sichtbar. „Feldgröße automatisch“ setzt Breite und Mindesthöhe zurück. Schriftgröße und Textfeldgröße sind getrennte Einstellungen.

Verlinkte Modellblöcke: Im Bearbeitungsmodus öffnet ein Klick auf Bild oder Text keine Zielseite. Titel, Vertretername und Kurzbeschreibung können bearbeitet werden. In der Vorschau und Teilnehmeransicht funktionieren die Links. Die Vertreter stehen in einer eigenen Zeile unter dem Modelltitel.

Lokaler Videoplayer: editor_server.py unterstützt für Video-/Audioassets einzelne HTTP-Bytebereiche (206/416), damit Vor- und Zurückspringen vor dem vollständigen Download funktioniert. Wiedergabe, Sprung zu späterer Stufe, deutsche VTT-Untertitel und aufklappbarer Stufentext auf der Glasl-Seite im Browser geprüft. Dienst für diese Ergänzung kontrolliert über die Editor-Schaltfläche neu gestartet; bestehender Editor-Token ausschließlich im Speicher übernommen, vorhandene Benutzer-Editoransichten nicht neu geladen.


## Modellseiten bearbeiten

In der Werkzeugleiste „Glasl“, „Watzlawick“ oder „Schulz von Thun“ auswählen. Direktzugriff auf Glasl: http://127.0.0.1:8767/lerneinheiten/glasl.html?editor=1 . Startseite weiterhin unter /editor. Die Modellseite bleibt unter ihrer ursprünglichen Adresse, damit relative Bild-, Video- und Untertitelpfade funktionieren. Im Editor sind die Stufentexte aufgeklappt. Texte und Überschriften anklicken und ändern, danach Speichern. Die Sprunglinks Erklärvideo, Lerntext und Quellen funktionieren auch im Bearbeitungsmodus.

Speichern prüft ausschließlich die ausgewählte, freigegebene Seite und deren Versionsstand. Sicherungen tragen den jeweiligen Dateinamen; andere Seiten bleiben unberührt. Beim Speichern der Glasl-Seite wird auch der TXT-Download aus dem aktuellen Lerntext und den Quellen erneuert und vorher gesichert. Die Quelldateien der Videoproduktion und die Videodatei werden dabei nicht verändert.
