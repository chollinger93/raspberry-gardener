package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"io/ioutil"
	"log"
	"net/http"
	"net/smtp"
	"os"
	"strconv"
	"sync"
	"time"

	"github.com/Masterminds/squirrel"
	_ "github.com/go-sql-driver/mysql"
	"github.com/gorilla/mux"
	"github.com/jmoiron/sqlx"
	"go.uber.org/zap"
)

var (
	host                = flag.String("host", "localhost", "Hostname")
	port                = flag.Int("port", 7777, "Port")
	enableNotifications = flag.Bool("enableNotifications", false, "Enable email notifications. Requires STMP variables to be set.")
)

func mustGetenv(k string) string {
	v := os.Getenv(k)
	if v == "" {
		log.Fatalf("Error: %s environment variable not set.\n", k)
	}
	return v
}

func configureConnectionPool(dbPool *sqlx.DB) {
	dbPool.SetMaxIdleConns(5)
	dbPool.SetMaxOpenConns(7)
	dbPool.SetConnMaxLifetime(1800)
}

func initTCPConnectionPool() (*sqlx.DB, error) {
	var (
		dbUser    = mustGetenv("DB_USER")
		dbPwd     = mustGetenv("DB_PASS")
		dbTCPHost = mustGetenv("DB_HOST")
		dbPort    = mustGetenv("DB_PORT")
		dbName    = mustGetenv("DB_NAME")
	)

	var dbURI string
	dbURI = fmt.Sprintf("%s:%s@tcp(%s:%s)/%s?parseTime=true", dbUser, dbPwd, dbTCPHost, dbPort, dbName)

	dbPool, err := sqlx.Open("mysql", dbURI)
	if err != nil {
		return nil, fmt.Errorf("sql.Open: %v", err)
	}

	configureConnectionPool(dbPool)
	return dbPool, nil
}

type App struct {
	Router  *mux.Router
	DB      *sqlx.DB
	SmtpCfg *SmtpConfig
}

func newApp(smtpCfg *SmtpConfig) *App {
	var err error
	app := &App{}
	//Database
	app.DB, err = initTCPConnectionPool()
	if err != nil {
		log.Fatalf("initTCPConnectionPool: unable to connect: %v", err)
	}
	// Create table it it doesn't exist
	// TODO:

	// router
	app.Router = mux.NewRouter()
	//r.Host("192.168.1.0/24")
	app.Router.HandleFunc("/", app.RetrieveSensorDataHandler).Methods(http.MethodPost)
	http.Handle("/", app.Router)

	// Other
	app.SmtpCfg = smtpCfg

	return app
}

type Sensor struct {
	SensorId      string
	TempC         float32
	VisLight      int32
	IrLight       int32
	UvIx          float32
	RawMoisture   int32
	VoltMoisture  float32
	Lumen         float32
	MeasurementTs string
}

func (a *App) storeData(sensors []Sensor) error {
	q := squirrel.Insert("data").Columns("sensorId", "tempC", "visLight", "irLight", "uvIx", "rawMoisture", "voltMoisture", "lumen", "measurementTs", "lastUpdateTimestamp")
	for _, s := range sensors {
		// RFC 3339
		measurementTs, err := time.Parse(time.RFC3339, s.MeasurementTs)
		if err != nil {
			zap.S().Errorf("Cannot parse TS %v to RFC3339", err)
			continue
		}
		q = q.Values(s.SensorId, s.TempC, s.VisLight, s.IrLight, s.UvIx, s.RawMoisture, s.VoltMoisture, s.Lumen, measurementTs, time.Now())
	}
	sql, args, err := q.ToSql()
	if err != nil {
		return err
	}

	res := a.DB.MustExec(sql, args...)
	zap.S().Info(res)
	return nil
}

func (a *App) sendErr(w http.ResponseWriter, msg string, code int) {
	response, _ := json.Marshal(msg)
	w.WriteHeader(code)
	w.Write(response)
	return
}

func (a *App) RetrieveSensorDataHandler(w http.ResponseWriter, r *http.Request) {
	var s []Sensor
	defer r.Body.Close()
	raw, err := ioutil.ReadAll(r.Body)
	if err != nil {
		zap.S().Error(err)
		a.sendErr(w, "Bad Request", http.StatusBadRequest)
		return
	}

	zap.S().Debugf("Raw: %v", string(raw))
	err = json.Unmarshal(raw, &s)
	if err != nil {
		zap.S().Error(err)
		a.sendErr(w, "Bad Request", http.StatusBadRequest)
		return
	}

	// Whether we successfully store or not, go validate those sensors
	go a.validateAllSensors(s)

	err = a.storeData(s)
	if err != nil {
		zap.S().Error(err)
		a.sendErr(w, "Bad Request", http.StatusBadRequest)
		return
	}
}

// Hard coded alert values for now
const MIN_TEMP_C = 5
const MAX_TEMP_C = 40
const LOW_MOISTURE_THRESHOLD_V = 2.2

// Simple mutex pattern to avoid race conditions
var mu sync.Mutex
var notificationTimeouts = map[string]time.Time{}

const NOTIFICATION_TIMEOUT = time.Duration(12 * time.Hour)

type SmtpConfig struct {
	smtpUser              string
	smtpPassword          string
	smtpAuthHost          string
	smtpSendHost          string
	notificationRecipient string
}

func NewSmtpConfig() *SmtpConfig {
	return &SmtpConfig{
		smtpUser:              mustGetenv("SMTP_USER"),
		smtpPassword:          mustGetenv("SMTP_PASSWORD"),
		smtpAuthHost:          mustGetenv("SMTP_AUTH_HOST"),
		smtpSendHost:          mustGetenv("SMTP_SEND_HOST"),
		notificationRecipient: mustGetenv("SMTP_NOTIFICATION_RECIPIENT"),
	}
}

func (a *App) notifyUser(sensor *Sensor) error {
	header := fmt.Sprintf("To: %s \r\n", a.SmtpCfg.notificationRecipient) +
		fmt.Sprintf("Subject: Sensor %v reached thresholds! \r\n", sensor.SensorId) +
		"\r\n"
	msg := header + fmt.Sprintf(`Sensor %s encountered the following threshold failure at %v:
	Temperature: %v (Thresholds: Min: %v / Max: %v)
	Moisture: %v (Thresholds: Min: %v / Max: N/A)`, sensor.SensorId, sensor.MeasurementTs,
		sensor.TempC, MIN_TEMP_C, MAX_TEMP_C, sensor.VoltMoisture, LOW_MOISTURE_THRESHOLD_V)
	zap.S().Warn(msg)
	// Get config
	// Auth to mail server
	auth := smtp.PlainAuth("", a.SmtpCfg.smtpUser, a.SmtpCfg.smtpPassword, a.SmtpCfg.smtpAuthHost)
	err := smtp.SendMail(a.SmtpCfg.smtpSendHost, auth, a.SmtpCfg.smtpUser,
		[]string{a.SmtpCfg.notificationRecipient}, []byte(msg))
	if err != nil {
		zap.S().Errorf("Error sending notification email: %v", err)
		return err
	}
	return nil
}

func (a *App) checkSensorThresholds(sensor *Sensor) bool {
	if sensor.VoltMoisture >= LOW_MOISTURE_THRESHOLD_V || sensor.TempC <= MIN_TEMP_C || sensor.TempC >= MAX_TEMP_C {
		return true
	}
	return false
}

func (a *App) validateSensor(sensor *Sensor) error {
	// Check the values first
	if !a.checkSensorThresholds(sensor) {
		zap.S().Debugf("Values for %s are below thresholds", sensor.SensorId)
		return nil
	}
	// Otherwise, notify
	mu.Lock()
	// If we already have the sensor stored in-memory, check whether its time to notify again
	if lastCheckedTime, ok := notificationTimeouts[sensor.SensorId]; ok {
		if time.Now().Sub(lastCheckedTime) < NOTIFICATION_TIMEOUT {
			// Not time yet
			zap.S().Debug("Timeout not reached")
			return nil
		}
	}
	// Reset the timer
	notificationTimeouts[sensor.SensorId] = time.Now()
	// Otherwise, notify
	err := a.notifyUser(sensor)
	// Release the mutex late
	mu.Unlock()
	return err
}

func structSliceToMap(structSlice []Sensor) map[string]Sensor {
	structMap := make(map[string]Sensor)
	for i := 0; i < len(structSlice); i += 2 {
		structMap[structSlice[i].SensorId] = structSlice[i+1]
	}
	return structMap
}

func (a *App) validateAllSensors(sensors []Sensor) {
	// Avoid duplicate key checks
	sensorMap := structSliceToMap(sensors)
	for _, sensor := range sensorMap {
		go a.validateSensor(&sensor)
	}
}

func main() {
	flag.Parse()
	// Logger
	logger, _ := zap.NewDevelopment()
	defer logger.Sync() // flushes buffer, if any
	zap.ReplaceGlobals(logger)

	// Check envs
	hostEnv := os.Getenv("APP_HOST")
	portEnv := os.Getenv("APP_PORT")
	if hostEnv != "" {
		*host = hostEnv
	}
	if portEnv != "" {
		*port, _ = strconv.Atoi(portEnv)
	}
	uri := fmt.Sprintf("%s:%v", *host, *port)

	// Check optional ones
	// TODO: config file
	var smtpCfg *SmtpConfig
	if *enableNotifications {
		smtpCfg = NewSmtpConfig()
	}

	app := newApp(smtpCfg)

	zap.S().Infof("Starting server on %s", uri)
	log.Fatal(http.ListenAndServe(uri, app.Router))
}
