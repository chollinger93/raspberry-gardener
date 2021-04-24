package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"io/ioutil"
	"log"
	"net/http"
	"os"
	"strconv"
	"time"

	"github.com/Masterminds/squirrel"
	_ "github.com/go-sql-driver/mysql"
	"github.com/gorilla/mux"
	"github.com/jmoiron/sqlx"
	"go.uber.org/zap"
)

var (
	host = flag.String("host", "localhost", "Hostname")
	port = flag.Int("port", 7777, "Port")
)

func mustGetenv(k string) string {
	v := os.Getenv(k)
	if v == "" {
		log.Fatalf("Warning: %s environment variable not set.\n", k)
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
	Router *mux.Router
	DB     *sqlx.DB
}

func newApp() *App {
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

	return app
}

type Sensor struct {
	SensorId     string
	TempC        float32
	VisLight     int32
	IrLight      int32
	UvIx         float32
	RawMoisture  int32
	VoltMoisture float32
}

func (a *App) storeData(sensors []Sensor) error {
	q := squirrel.Insert("data").Columns("sensorId", "tempC", "visLight", "irLight", "uvIx", "rawMoisture", "voltMoisture", "lastUpdateTimestamp")
	for _, s := range sensors {
		q = q.Values(s.SensorId, s.TempC, s.VisLight, s.IrLight, s.UvIx, s.RawMoisture, s.VoltMoisture, time.Now())
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

	err = a.storeData(s)
	if err != nil {
		zap.S().Error(err)
		a.sendErr(w, "Bad Request", http.StatusBadRequest)
		return
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

	app := newApp()

	zap.S().Infof("Starting server on %s", uri)
	log.Fatal(http.ListenAndServe(uri, app.Router))
}
