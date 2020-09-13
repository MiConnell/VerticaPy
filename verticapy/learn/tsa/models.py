# (c) Copyright [2018-2020] Micro Focus or one of its affiliates.
# Licensed under the Apache License, Version 2.0 (the "License");
# You may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# |_     |~) _  _| _  /~\    _ |.
# |_)\/  |_)(_|(_||   \_/|_|(_|||
#    /
#              ____________       ______
#             / __        `\     /     /
#            |  \/         /    /     /
#            |______      /    /     /
#                   |____/    /     /
#          _____________     /     /
#          \           /    /     /
#           \         /    /     /
#            \_______/    /     /
#             ______     /     /
#             \    /    /     /
#              \  /    /     /
#               \/    /     /
#                    /     /
#                   /     /
#                   \    /
#                    \  /
#                     \/
#                    _
# \  / _  __|_. _ _ |_)
#  \/ (/_|  | |(_(_|| \/
#                     /
# VerticaPy is a Python library with scikit-like functionality to use to conduct
# data science projects on data stored in Vertica, taking advantage Vertica’s
# speed and built-in analytics and machine learning features. It supports the
# entire data science life cycle, uses a ‘pipeline’ mechanism to sequentialize
# data transformation operations, and offers beautiful graphical options.
#
# VerticaPy aims to solve all of these problems. The idea is simple: instead
# of moving data around for processing, VerticaPy brings the logic to the data.
#
#
# Modules
#
# Standard Python Modules
import math

# VerticaPy Modules
from verticapy.learn.vmodel import *
from verticapy.connections.connect import read_auto_connect
from verticapy.learn.linear_model import ElasticNet
from verticapy import vDataFrame

# Other Python Modules
from dateutil.parser import parse

# ---#
class SARIMAX(Regressor):
    """
---------------------------------------------------------------------------
Creates an SARIMAX object by using the Vertica Highly Distributed and 
Scalable Linear Regression on the data.

Parameters
----------
name: str
    Name of the the model. The model will be stored in the DB.
cursor: DBcursor, optional
    Vertica DB cursor.
p: int, optional
    Order of the AR (Auto-Regressive) part.
d: int, optional
    Order of the I (Integrated) part.
q: int, optional
    Order of the MA (Moving-Average) part.
P: int, optional
    Order of the seasonal AR (Auto-Regressive) part.
D: int, optional
    Order of the seasonal I (Integrated) part.
Q: int, optional
    Order of the seasonal MA (Moving-Average) part.
s: int, optional
    Span of the seasonality.
penalty: str, optional
    Determines the method of regularization.
        None : No Regularization
        L1   : L1 Regularization
        L2   : L2 Regularization
        ENet : Combination between L1 and L2
tol: float, optional
    Determines whether the algorithm has reached the specified accuracy result.
C: float, optional
    The regularization parameter value. The value must be zero or non-negative.
max_iter: int, optional
    Determines the maximum number of iterations the algorithm performs before 
    achieving the specified accuracy result.
solver: str, optional
    The optimizer method to use to train the model. 
        Newton : Newton Method
        BFGS   : Broyden Fletcher Goldfarb Shanno
        CGD    : Coordinate Gradient Descent
l1_ratio: float, optional
    ENet mixture parameter that defines how much L1 versus L2 regularization 
    to provide.
max_pik: int, optional
    Number of inverse MA coefficient used to approximate the MA.
papprox_ma: int, optional
    the p of the AR(p) used to approximate the MA coefficients.
    """

    def __init__(
        self,
        name: str,
        cursor=None,
        p: int = 1,
        d: int = 0,
        q: int = 0,
        P: int = 0,
        D: int = 0,
        Q: int = 0,
        s: int = 0,
        penalty: str = "None",
        tol: float = 1e-4,
        C: float = 1.0,
        max_iter: int = 1000,
        solver: str = "Newton",
        l1_ratio: float = 0.5,
        max_pik: int = 100,
        papprox_ma: int = 200,
    ):
        check_types([("name", name, [str],)])
        self.type, self.name = "SARIMAX", name
        self.set_params(
            {
                "p": p,
                "d": d,
                "q": q,
                "P": P,
                "D": D,
                "Q": Q,
                "s": s,
                "penalty": penalty,
                "tol": tol,
                "C": C,
                "max_iter": max_iter,
                "solver": solver,
                "l1_ratio": l1_ratio,
                "max_pik": max_pik,
                "papprox_ma": papprox_ma,
            }
        )
        if self.parameters["s"] == 0:
            assert (
                self.parameters["D"] == 0
                and self.parameters["P"] == 0
                and self.parameters["Q"] == 0
            ), ParameterError(
                "In case of non-seasonality (s = 0), all the parameters P, D or Q must be equal to 0."
            )
        else:
            assert (
                self.parameters["D"] > 0
                or self.parameters["P"] > 0
                or self.parameters["Q"] > 0
            ), ParameterError(
                "In case of seasonality (s > 0), at least one of the parameters P, D or Q must be strictly greater than 0."
            )
        if not (cursor):
            cursor = read_auto_connect().cursor()
        else:
            check_cursor(cursor)
        self.cursor = cursor
        version(cursor=cursor, condition=[8, 0, 0])

    # ---#
    def deploySQL(self):
        """
    ---------------------------------------------------------------------------
    Returns the SQL code needed to deploy the model.

    Returns
    -------
    str
        the SQL code needed to deploy the model.
        """
        sql = self.deploy_predict_
        if (self.parameters["d"] > 0) or (
            self.parameters["D"] > 0 and self.parameters["s"] > 0
        ):
            for i in range(0, self.parameters["d"] + 1):
                for k in range(
                    0, max((self.parameters["D"] + 1) * min(1, self.parameters["s"]), 1)
                ):
                    if (k, i) != (0, 0):
                        comb_i_d = (
                            math.factorial(self.parameters["d"])
                            / math.factorial(self.parameters["d"] - i)
                            / math.factorial(i)
                        )
                        comb_k_D = (
                            math.factorial(self.parameters["D"])
                            / math.factorial(self.parameters["D"] - k)
                            / math.factorial(k)
                        )
                        sql += " + {} * LAG(VerticaPy_y_copy, {}) OVER (ORDER BY [VerticaPy_ts])".format(
                            (-1) ** (i + k + 1) * comb_i_d * comb_k_D,
                            i + self.parameters["s"] * k,
                        )
        return sql

    # ---#
    def fpredict(self, L: list):
        """
    ---------------------------------------------------------------------------
    Computes the prediction.

    Parameters
    ----------
    L: list
        List containing the data. It must be a 2D list containing multiple rows.
        Each row must include as first element the ordered predictor and as 
        nth elements the nth - 1 exogenous variable (nth > 2). 

    Returns
    -------
    float
        the prediction.
        """

        def sub_arp(L: list):
            L_final = []
            for i in range(len(L)):
                result = L[-i]
                for i in range(len(self.coef_.values["coefficient"])):
                    elem = self.coef_.values["predictor"][i]
                    if elem.lower() == "intercept":
                        result -= self.coef_.values["coefficient"][i]
                    elif elem.lower()[0:2] == "ar":
                        nb = int(elem[2:])
                        try:
                            result -= self.coef_.values["coefficient"][i] * L[-nb]
                        except:
                            result = None
                    L_final = [result] + L_final
            return L_final

        def fepsilon(L: list):
            if self.parameters["p"] > 0 or self.parameters["P"] > 0:
                L_tmp = sub_arp(L)
            else:
                L_tmp = L
            try:
                result = L_tmp[-1] - self.ma_avg_
                for i in range(1, self.parameters["max_pik"]):
                    result -= self.ma_piq_.values["coefficient"][i] * (
                        L_tmp[-i] - self.ma_avg_
                    )
                return result
            except:
                return 0

        if (
            self.parameters["p"] == 0
            and self.parameters["q"] == 0
            and self.parameters["d"] == 0
            and self.parameters["s"] == 0
            and not (self.exogenous)
        ):
            return self.ma_avg_
        try:
            yt = [elem[0] for elem in L]
            yt_copy = [elem[0] for elem in L]
            yt.reverse()
            if self.parameters["d"] > 0:
                for i in range(self.parameters["d"]):
                    yt = [yt[i - 1] - yt[i] for i in range(1, len(yt))]
            if self.parameters["D"] > 0 and self.parameters["s"] > 0:
                for i in range(self.parameters["D"]):
                    yt = [
                        yt[i - self.parameters["s"]] - yt[i]
                        for i in range(self.parameters["s"], len(yt))
                    ]
            yt.reverse()
            result, j = 0, 1
            for i in range(len(self.coef_.values["coefficient"])):
                elem = self.coef_.values["predictor"][i]
                if elem.lower() == "intercept":
                    result += self.coef_.values["coefficient"][i]
                elif elem.lower()[0:2] == "ar":
                    nb = int(elem[2:])
                    result += self.coef_.values["coefficient"][i] * yt[-nb]
                elif elem.lower()[0:2] == "ma":
                    nb = int(elem[2:])
                    result += self.coef_.values["coefficient"][i] * fepsilon(
                        yt[: -nb - 1]
                    )
                else:
                    result += self.coef_.values["coefficient"][i] * L[-1][j]
                    j += 1
            for i in range(0, self.parameters["d"] + 1):
                for k in range(
                    0, max((self.parameters["D"] + 1) * min(1, self.parameters["s"]), 1)
                ):
                    if (k, i) != (0, 0):
                        comb_i_d = (
                            math.factorial(self.parameters["d"])
                            / math.factorial(self.parameters["d"] - i)
                            / math.factorial(i)
                        )
                        comb_k_D = (
                            math.factorial(self.parameters["D"])
                            / math.factorial(self.parameters["D"] - k)
                            / math.factorial(k)
                        )
                        result += (
                            (-1) ** (i + k + 1)
                            * comb_i_d
                            * comb_k_D
                            * yt_copy[-(i + self.parameters["s"] * k)]
                        )
            return result
        except:
            return None

    # ---#
    def fit(
        self,
        input_relation: str,
        y: str,
        ts: str,
        X: list = [],
        test_relation: str = "",
    ):
        """
    ---------------------------------------------------------------------------
    Trains the model.

    Parameters
    ----------
    input_relation: str
        Train relation.
    y: str
        Response column.
    ts: str
        vcolumn used to order the data.
    X: list, optional
        exogenous columns used to fit the model.
    test_relation: str, optional
        Relation to use to test the self.

    Returns
    -------
    object
        model
        """
        check_types(
            [
                ("input_relation", input_relation, [str],),
                ("y", y, [str],),
                ("test_relation", test_relation, [str],),
                ("ts", ts, [str],),
            ]
        )
        # Initialization
        check_model(name=self.name, cursor=self.cursor)
        self.input_relation = input_relation
        self.test_relation = test_relation if (test_relation) else input_relation
        self.y, self.ts, self.deploy_predict_ = str_column(y), str_column(ts), ""
        self.coef_ = tablesample({"predictor": [], "coefficient": []})
        X, schema = [str_column(elem) for elem in X], schema_relation(self.name)[0]
        self.X, self.exogenous = [], X
        relation = (
            "(SELECT *, [VerticaPy_y] AS VerticaPy_y_copy FROM {}) VERTICAPY_SUBTABLE "
        )
        model = ElasticNet(
            name=self.name,
            solver=self.parameters["solver"],
            max_iter=self.parameters["max_iter"],
            tol=self.parameters["tol"],
            penalty=self.parameters["penalty"],
            l1_ratio=self.parameters["l1_ratio"],
            C=self.parameters["C"],
        )

        if (
            self.parameters["p"] == 0
            and self.parameters["q"] == 0
            and self.parameters["d"] == 0
            and self.parameters["s"] == 0
            and not (self.exogenous)
        ):
            query = "SELECT AVG({}) FROM {}".format(self.y, self.input_relation)
            self.ma_avg_ = self.cursor.execute(query).fetchone()[0]
            self.deploy_predict_ = str(self.ma_avg_)

        # I(d)
        if self.parameters["d"] > 0:
            for i in range(self.parameters["d"]):
                relation = "(SELECT [VerticaPy_y] - LAG([VerticaPy_y], 1) OVER (ORDER BY [VerticaPy_ts]) AS [VerticaPy_y], VerticaPy_y_copy[VerticaPy_key_columns] FROM {}) VERTICAPY_SUBTABLE".format(
                    relation
                )
        if self.parameters["D"] > 0 and self.parameters["s"] > 0:
            for i in range(self.parameters["D"]):
                relation = "(SELECT [VerticaPy_y] - LAG([VerticaPy_y], {}) OVER (ORDER BY [VerticaPy_ts]) AS [VerticaPy_y], VerticaPy_y_copy[VerticaPy_key_columns] FROM {}) VERTICAPY_SUBTABLE".format(
                    self.parameters["s"], relation
                )

        # AR(p)
        if self.parameters["p"] > 0 or self.parameters["P"] > 0:
            columns = [
                "LAG([VerticaPy_y], {}) OVER (ORDER BY [VerticaPy_ts]) AS AR{}".format(
                    i, i
                )
                for i in range(1, self.parameters["p"] + 1)
            ]
            AR = ["AR{}".format(i) for i in range(1, self.parameters["p"] + 1)]
            if self.parameters["s"] > 0:
                for i in range(1, self.parameters["P"] + 1):
                    if (i * self.parameters["s"]) not in (
                        range(1, self.parameters["p"] + 1)
                    ):
                        columns += [
                            "LAG([VerticaPy_y], {}) OVER (ORDER BY [VerticaPy_ts]) AS AR{}".format(
                                i * self.parameters["s"], i * self.parameters["s"]
                            )
                        ]
                        AR += ["AR{}".format(i * self.parameters["s"])]
            relation = "(SELECT *, {} FROM {}) VERTICAPY_SUBTABLE".format(
                ", ".join(columns), relation
            )
            try:
                drop_view(
                    "{}.VERTICAPY_TEMP_MODEL_LINEAR_REGRESSION_VIEW_".format(schema),
                    print_info=False,
                )
            except:
                pass
            query = "CREATE VIEW {}.VERTICAPY_TEMP_MODEL_LINEAR_REGRESSION_VIEW_ AS SELECT * FROM {}".format(
                schema,
                relation.format(self.input_relation)
                .replace("[VerticaPy_ts]", self.ts)
                .replace("[VerticaPy_y]", self.y)
                .replace("[VerticaPy_key_columns]", ", " + ", ".join([self.ts] + X)),
            )
            self.cursor.execute(query)
            self.X += AR + X
            model.fit(
                input_relation="{}.VERTICAPY_TEMP_MODEL_LINEAR_REGRESSION_VIEW_".format(
                    schema
                ),
                X=self.X,
                y=self.y,
            )
            drop_view(
                "{}.VERTICAPY_TEMP_MODEL_LINEAR_REGRESSION_VIEW_".format(schema),
                print_info=False,
            )
            self.coef_.values["predictor"] = model.coef_.values["predictor"]
            self.coef_.values["coefficient"] = model.coef_.values["coefficient"]
            alphaq = model.coef_.values["coefficient"]
            model.drop()
            epsilon_final = (
                "[VerticaPy_y] - "
                + str(alphaq[0])
                + " - "
                + " - ".join(
                    [
                        str(alphaq[i])
                        + " * "
                        + "LAG([VerticaPy_y], {}) OVER (ORDER BY [VerticaPy_ts])".format(
                            i
                        )
                        for i in range(1, self.parameters["p"] + 1)
                    ]
                )
            )
            self.deploy_predict_ = (
                str(alphaq[0])
                + " + "
                + " + ".join(
                    [
                        str(alphaq[i])
                        + " * "
                        + "LAG(VerticaPy_y_copy, {}) OVER (ORDER BY [VerticaPy_ts])".format(
                            i
                        )
                        for i in range(1, self.parameters["p"] + 1)
                    ]
                )
            )
            if self.parameters["s"] > 0 and self.parameters["P"] > 0:
                epsilon_final += " - " + " - ".join(
                    [
                        str(alphaq[i])
                        + " * "
                        + "LAG([VerticaPy_y], {}) OVER (ORDER BY [VerticaPy_ts])".format(
                            i * self.parameters["s"]
                        )
                        for i in range(
                            self.parameters["p"] + 1,
                            self.parameters["p"]
                            + (self.parameters["P"] if self.parameters["s"] > 0 else 0)
                            + 1,
                        )
                    ]
                )
                self.deploy_predict_ += " + " + " + ".join(
                    [
                        str(alphaq[i])
                        + " * "
                        + "LAG(VerticaPy_y_copy, {}) OVER (ORDER BY [VerticaPy_ts])".format(
                            i * self.parameters["s"]
                        )
                        for i in range(
                            self.parameters["p"] + 1,
                            self.parameters["p"]
                            + (self.parameters["P"] if self.parameters["s"] > 0 else 0)
                            + 1,
                        )
                    ]
                )
            for idx, elem in enumerate(X):
                epsilon_final += " - {} * [X{}]".format(
                    alphaq[
                        idx
                        + self.parameters["p"]
                        + (self.parameters["P"] if self.parameters["s"] > 0 else 0)
                        + 1
                    ],
                    idx,
                )
                self.deploy_predict_ += " + {} * [X{}]".format(
                    alphaq[
                        idx
                        + self.parameters["p"]
                        + (self.parameters["P"] if self.parameters["s"] > 0 else 0)
                        + 1
                    ],
                    idx,
                )
            relation = "(SELECT {} AS [VerticaPy_y], {}, VerticaPy_y_copy[VerticaPy_key_columns] FROM {}) VERTICAPY_SUBTABLE".format(
                epsilon_final, ", ".join(AR), relation
            )

        # MA(q)
        if self.parameters["q"] > 0 or (
            self.parameters["Q"] > 0 and self.parameters["s"] > 0
        ):
            transform_relation = relation.replace("[VerticaPy_y]", y).replace(
                "[VerticaPy_ts]", ts
            )
            transform_relation = transform_relation.replace(
                "[VerticaPy_key_columns]", ", " + ", ".join(X + [ts])
            )
            for idx, elem in enumerate(X):
                transform_relation = transform_relation.replace(
                    "[X{}]".format(idx), elem
                )
            query = "SELECT COUNT(*), AVG({}) FROM {}".format(
                self.y, transform_relation.format(input_relation)
            )
            result = self.cursor.execute(query).fetchone()
            self.ma_avg_ = result[1]
            n = result[0]
            n = max(
                max(
                    min(max(n ** (1.0 / 3.0), 8), self.parameters["papprox_ma"]),
                    self.parameters["q"],
                ),
                self.parameters["Q"] * self.parameters["s"] + 1,
            )
            columns = [
                "LAG([VerticaPy_y], {}) OVER (ORDER BY [VerticaPy_ts]) AS ARq{}".format(
                    i, i
                )
                for i in range(1, n)
            ]
            ARq = ["ARq{}".format(i) for i in range(1, n)]
            tmp_relation = "(SELECT *, {} FROM {}) VERTICAPY_SUBTABLE".format(
                ", ".join(columns), relation
            )
            for idx, elem in enumerate(X):
                tmp_relation = tmp_relation.replace("[X{}]".format(idx), elem)
            try:
                drop_view(
                    "{}.VERTICAPY_TEMP_MODEL_LINEAR_REGRESSION_VIEW_".format(schema),
                    print_info=False,
                )
            except:
                pass
            query = "CREATE VIEW {}.VERTICAPY_TEMP_MODEL_LINEAR_REGRESSION_VIEW_ AS SELECT * FROM {}".format(
                schema,
                tmp_relation.format(self.input_relation)
                .replace("[VerticaPy_ts]", self.ts)
                .replace("[VerticaPy_y]", self.y)
                .replace("[VerticaPy_key_columns]", ", " + ", ".join([self.ts] + X)),
            )
            self.cursor.execute(query)
            model.fit(
                input_relation="{}.VERTICAPY_TEMP_MODEL_LINEAR_REGRESSION_VIEW_".format(
                    schema
                ),
                X=ARq,
                y=self.y,
            )
            drop_view(
                "{}.VERTICAPY_TEMP_MODEL_LINEAR_REGRESSION_VIEW_".format(schema),
                print_info=False,
            )
            if not (self.coef_.values["predictor"]):
                self.coef_.values["predictor"] += ["Intercept"]
                self.coef_.values["coefficient"] += [self.ma_avg_]
                self.deploy_predict_ = str(self.ma_avg_)
            alphaq = model.coef_.values["coefficient"][1:]
            model.drop()
            thetaq, piq = [], [-1] + []
            for j in range(0, len(alphaq)):
                thetaq += [
                    sum([alphaq[j - i - 1] * thetaq[i] for i in range(0, j)])
                    + alphaq[j]
                ]
            for j in range(self.parameters["q"]):
                self.coef_.values["predictor"] += ["ma{}".format(j + 1)]
                self.coef_.values["coefficient"] += [thetaq[j]]
                self.deploy_predict_ += " + {} * MA{}".format(thetaq[j], j + 1)
            if self.parameters["s"] > 0:
                for j in range(1, self.parameters["Q"] + 1):
                    self.coef_.values["predictor"] += [
                        "ma{}".format(self.parameters["s"] * j)
                    ]
                    self.coef_.values["coefficient"] += [
                        thetaq[self.parameters["s"] * j - 1]
                    ]
                    self.deploy_predict_ += " + {} * MA{}".format(
                        thetaq[self.parameters["s"] * j - 1], self.parameters["s"] * j
                    )
            for j in range(0, self.parameters["max_pik"]):
                piq_tmp = 0
                for i in range(0, self.parameters["q"]):
                    if j - i > 0:
                        piq_tmp -= thetaq[i] * piq[j - i]
                    elif j - i == 0:
                        piq_tmp -= thetaq[i]
                piq = piq + [piq_tmp]
            self.ma_piq_ = tablesample({"coefficient": piq})
            epsilon = (
                "[VerticaPy_y] - "
                + str(self.ma_avg_)
                + " - "
                + " - ".join(
                    [
                        str((piq[i]))
                        + " * "
                        + "LAG([VerticaPy_y] - {}, {}) OVER (ORDER BY [VerticaPy_ts])".format(
                            self.ma_avg_, i
                        )
                        for i in range(1, self.parameters["max_pik"])
                    ]
                )
            )
            epsilon += " AS MA0"
            relation = "(SELECT *, {} FROM {}) VERTICAPY_SUBTABLE".format(
                epsilon, relation
            )
            columns = [
                "LAG(MA0, {}) OVER (ORDER BY [VerticaPy_ts]) AS MA{}".format(i, i)
                for i in range(1, self.parameters["q"] + 1)
            ]
            MA = ["MA{}".format(i) for i in range(1, self.parameters["q"] + 1)]
            if self.parameters["s"] > 0:
                columns += [
                    "LAG(MA0, {}) OVER (ORDER BY [VerticaPy_ts]) AS MA{}".format(
                        i * self.parameters["s"], i * self.parameters["s"]
                    )
                    for i in range(1, self.parameters["Q"] + 1)
                ]
                MA += [
                    "MA{}".format(i * self.parameters["s"])
                    for i in range(1, self.parameters["Q"] + 1)
                ]
            relation = "(SELECT *, {} FROM {}) VERTICAPY_SUBTABLE".format(
                ", ".join(columns), relation
            )
            self.X += MA
            transform_relation = relation.replace("[VerticaPy_y]", y).replace(
                "[VerticaPy_ts]", ts
            )
            transform_relation = transform_relation.replace(
                "[VerticaPy_key_columns]", ", " + ", ".join(X + [ts])
            )
            for idx, elem in enumerate(X):
                transform_relation = transform_relation.replace(
                    "[X{}]".format(idx), elem
                )
        self.transform_relation = relation
        return self

    # ---#
    def plot(
        self,
        vdf,
        y: str = "",
        ts: str = "",
        X: list = [],
        dynamic: bool = False,
        one_step: bool = True,
        observed: bool = True,
        confidence: bool = True,
        nlead: int = 10,
        nlast: int = 0,
        limit: int = 1000,
    ):
        """
    ---------------------------------------------------------------------------
    Draws the Plot of the prediction.

    Parameters
    ----------
    vdf: vDataFrame
        Object to use to run the prediction.
    y: str, optional
        Response column.
    ts: str, optional
        vcolumn used to order the data.
    X: list, optional
        exogenous vcolumns.
    dynamic: bool, optional
        If set to True, the dynamic forecast will be drawn.
    one_step: bool, optional
        If set to True, the one step ahead forecast will be drawn.
    observed: bool, optional
        If set to True, the observation will be drawn.
    confidence: bool, optional
        If set to True, the confidence ranges will be drawn.
    nlead: int, optional
        Number of leads to predict after the last ts date.
    limit: int, optional
        Maximum number of past elements to use.

    Returns
    -------
    Figure
        Matplotlib Figure
        """
        check_types(
            [
                ("limit", limit, [int, float],),
                ("nlead", nlead, [int, float],),
                ("dynamic", dynamic, [bool],),
                ("observed", observed, [bool],),
                ("one_step", one_step, [bool],),
                ("confidence", confidence, [bool],),
                ("vdf", vdf, [vDataFrame],),
            ],
        )
        delta_limit, limit = (
            limit,
            max(
                max(
                    limit,
                    self.parameters["p"] + 1 + nlast,
                    self.parameters["P"] * self.parameters["s"] + 1 + nlast,
                ),
                200,
            ),
        )
        delta_limit = max(limit - delta_limit - nlast, 0)
        assert dynamic or one_step or observed, ParameterError(
            "No option selected.\n You should set either dynamic, one_step or observed to True."
        )
        assert nlead + nlast > 0 or not (dynamic), ParameterError(
            "Dynamic Plots are only possible if either parameter 'nlead' is greater than 0 or parameter 'nlast' is greater than 0, and parameter 'dynamic' is set to True."
        )
        if dynamic:
            assert not (self.exogenous), Exception(
                "Dynamic Plots are only possible for SARIMA models (no exegenous variables), not SARIMAX."
            )
        if not (y):
            y = self.y
        if not (ts):
            ts = self.ts
        if not (X):
            X = self.exogenous
        result = self.predict(
            vdf=vdf, y=y, ts=ts, X=X, nlead=0, name="_verticapy_prediction_"
        )
        error_eps = 1.96 * math.sqrt(self.score(method="mse"))
        result = (
            result.select([ts, y, "_verticapy_prediction_"])
            .dropna(print_info=False)
            .sort([ts])
            .tail(limit)
            .values
        )
        columns = [elem for elem in result]
        if isinstance(result[columns[0]][0], str):
            result[columns[0]] = [parse(elem) for elem in result[columns[0]]]
        true_value = [result[columns[0]], result[columns[1]]]
        one_step_ahead = [result[columns[0]], result[columns[2]]]
        lower_osa, upper_osa = (
            [
                float(elem) - error_eps if elem != None else None
                for elem in one_step_ahead[1]
            ],
            [
                float(elem) + error_eps if elem != None else None
                for elem in one_step_ahead[1]
            ],
        )
        if dynamic:
            deltat = result[columns[0]][-1] - result[columns[0]][-2]
            lead_time_list = []
            if nlast > 0:
                lead_list = [[elem] for elem in result[columns[1]][:-nlast]]
            else:
                lead_list = [[elem] for elem in result[columns[1]]]
            for i in range(nlast):
                lead_list += [[self.fpredict(lead_list)]]
                lead_time_list += [result[columns[0]][i - nlast]]
            if lead_time_list:
                start_time = lead_time_list[-1]
            else:
                start_time = result[columns[0]][-1]
            for i in range(nlead):
                lead_list += [[self.fpredict(lead_list)]]
                lead_time_list += [start_time + (i + 1) * deltat]
            dynamic_forecast = (
                [result[columns[0]][-nlast - 1]] + lead_time_list,
                [result[columns[1]][-nlast - 1]]
                + [elem[0] for elem in lead_list[-nlast - nlead :]],
            )
            lower_d, upper_d = [], []
            for i in range(len(dynamic_forecast[1])):
                if (
                    self.parameters["s"] > 0
                    and self.parameters["p"] == 0
                    and self.parameters["d"] == 0
                    and self.parameters["q"] == 0
                ):
                    delta_error = error_eps * math.sqrt(
                        int(i / self.parameters["s"]) + 1
                    )
                else:
                    delta_error = error_eps * math.sqrt(i + 1)
                lower_d += [float(dynamic_forecast[1][i]) - delta_error]
                upper_d += [float(dynamic_forecast[1][i]) + delta_error]
        else:
            lower_d, upper_d, dynamic_forecast = [], [], ([], [])
        import matplotlib.pyplot as plt

        alpha = 0.3
        plt.figure(figsize=(12, 9)) if isnotebook() else plt.figure(figsize=(10, 6))
        plt.gca().grid()
        if dynamic:
            plt.fill_between(
                dynamic_forecast[0],
                1.02
                * float(min(true_value[1] + dynamic_forecast[1] + one_step_ahead[1])),
                1.02
                * float(max(true_value[1] + dynamic_forecast[1] + one_step_ahead[1])),
                alpha=0.04,
                color="#0073E7",
            )
            if confidence:
                plt.fill_between(
                    dynamic_forecast[0], lower_d, upper_d, alpha=0.08, color="#555555"
                )
                plt.plot(dynamic_forecast[0], lower_d, alpha=0.08, color="#000000")
                plt.plot(dynamic_forecast[0], upper_d, alpha=0.08, color="#000000")
            plt.plot(
                dynamic_forecast[0],
                dynamic_forecast[1],
                color="#FE5016",
                label="Dynamic Forecast",
                linestyle="dashed",
                linewidth=2,
            )
        if one_step:
            if confidence:
                plt.fill_between(
                    one_step_ahead[0][delta_limit:],
                    lower_osa[delta_limit:],
                    upper_osa[delta_limit:],
                    alpha=0.04,
                    color="#555555",
                )
                plt.plot(
                    one_step_ahead[0][delta_limit:],
                    lower_osa[delta_limit:],
                    alpha=0.04,
                    color="#000000",
                )
                plt.plot(
                    one_step_ahead[0][delta_limit:],
                    upper_osa[delta_limit:],
                    alpha=0.04,
                    color="#000000",
                )
            plt.plot(
                one_step_ahead[0][delta_limit:],
                one_step_ahead[1][delta_limit:],
                color="#19A26B",
                label="One-step ahead Forecast",
                linestyle=":",
                linewidth=2,
            )
        if observed:
            plt.plot(
                true_value[0][delta_limit:],
                true_value[1][delta_limit:],
                color="#0073E7",
                label="Observed",
                linewidth=2,
            )
        plt.rcParams["axes.facecolor"] = "#F2F2F2"
        plt.title(
            "SARIMAX({},{},{})({},{},{})_{}".format(
                self.parameters["p"],
                self.parameters["d"],
                self.parameters["q"],
                self.parameters["P"],
                self.parameters["D"],
                self.parameters["Q"],
                self.parameters["s"],
            )
        )
        plt.xticks(rotation=90)
        plt.subplots_adjust(bottom=0.24)
        plt.xlabel(ts)
        plt.legend(loc="center left", bbox_to_anchor=[1, 0.5])
        plt.ylim(
            1.02 * float(min(true_value[1] + dynamic_forecast[1] + one_step_ahead[1])),
            1.02 * float(max(true_value[1] + dynamic_forecast[1] + one_step_ahead[1])),
        )
        return plt.gcf()

    # ---#
    def predict(
        self,
        vdf,
        y: str = "",
        ts: str = "",
        X: list = [],
        nlead: int = 0,
        name: str = "",
    ):
        """
    ---------------------------------------------------------------------------
    Predicts using the input relation.

    Parameters
    ----------
    vdf: vDataFrame
        Object to use to run the prediction.
    y: str, optional
        Response column.
    ts: str, optional
        vcolumn used to order the data.
    X: list, optional
        exogenous vcolumns.
    nlead: int, optional
        Number of leads to predict after the last ts date.
    name: str, optional
        Name of the added vcolumn. If empty, a name will be generated.

    Returns
    -------
    vDataFrame
        object including the prediction.
        """
        check_types(
            [
                ("name", name, [str],),
                ("y", y, [str],),
                ("ts", ts, [str],),
                ("X", X, [list],),
                ("nlead", nlead, [int, float],),
                ("vdf", vdf, [vDataFrame],),
            ],
        )
        if not (y):
            y = self.y
        if not (ts):
            ts = self.ts
        if not (X):
            X = self.exogenous
        columns_check([y, ts], vdf)
        y, ts = vdf_columns_names([y, ts], vdf)
        name = (
            "{}_".format(self.type) + "".join(ch for ch in self.name if ch.isalnum())
            if not (name)
            else name
        )
        key_columns = ", " + ", ".join(vdf.get_columns(exclude_columns=[y]))
        transform_relation = self.transform_relation.replace(
            "[VerticaPy_y]", y
        ).replace("[VerticaPy_ts]", ts)
        transform_relation = transform_relation.replace(
            "[VerticaPy_key_columns]", key_columns
        )
        predictSQL = self.deploySQL().replace("[VerticaPy_y]", y).replace(
            "[VerticaPy_ts]", ts
        ) + " AS {}".format(name)
        for idx, elem in enumerate(X):
            transform_relation = transform_relation.replace("[X{}]".format(idx), elem)
            predictSQL = predictSQL.replace("[X{}]".format(idx), elem)
        columns = (
            vdf.get_columns(exclude_columns=[y])
            + [predictSQL]
            + ["VerticaPy_y_copy AS {}".format(y)]
        )
        relation = vdf.__genSQL__()
        for i in range(nlead):
            query = "SELECT ({} - LAG({}, 1) OVER (ORDER BY {}))::VARCHAR FROM {} ORDER BY {} DESC LIMIT 1".format(
                ts, ts, ts, relation, ts
            )
            deltat = vdf._VERTICAPY_VARIABLES_["cursor"].execute(query).fetchone()[0]
            query = "SELECT (MAX({}) + '{}'::interval)::VARCHAR FROM {}".format(
                ts, deltat, relation
            )
            next_t = vdf._VERTICAPY_VARIABLES_["cursor"].execute(query).fetchone()[0]
            if i == 0:
                first_t = next_t
            new_line = "SELECT '{}'::TIMESTAMP AS {}, {}".format(
                next_t,
                ts,
                ", ".join(
                    [
                        "NULL AS {}".format(column)
                        for column in vdf.get_columns(exclude_columns=[ts])
                    ]
                ),
            )
            relation_tmp = "(SELECT {} FROM {} UNION ALL ({})) VERTICAPY_SUBTABLE".format(
                ", ".join([ts] + vdf.get_columns(exclude_columns=[ts])),
                relation,
                new_line,
            )
            query = "SELECT {} FROM {} ORDER BY {} DESC LIMIT 1".format(
                self.deploySQL()
                .replace("[VerticaPy_y]", y)
                .replace("[VerticaPy_ts]", ts),
                transform_relation.format(relation_tmp),
                ts,
            )
            prediction = (
                vdf._VERTICAPY_VARIABLES_["cursor"].execute(query).fetchone()[0]
            )
            columns_tmp = vdf.get_columns(exclude_columns=[ts, y])
            new_line = "SELECT '{}'::TIMESTAMP AS {}, {} AS {} {}".format(
                next_t,
                ts,
                prediction,
                y,
                (", " if (columns_tmp) else "")
                + ", ".join(["NULL AS {}".format(column) for column in columns_tmp]),
            )
            relation = "(SELECT {} FROM {} UNION ALL ({})) VERTICAPY_SUBTABLE".format(
                ", ".join([ts, y] + vdf.get_columns(exclude_columns=[ts, y])),
                relation,
                new_line,
            )
        final_relation = "(SELECT {} FROM {}) VERTICAPY_SUBTABLE".format(
            ", ".join(columns), transform_relation.format(relation)
        )
        result = vdf_from_relation(final_relation, "SARIMAX", self.cursor,)
        if nlead > 0:
            result[y].apply(
                "CASE WHEN {} >= '{}' THEN NULL ELSE {} END".format(ts, first_t, "{}")
            )
        return result


# ---#
class VAR(Regressor):
    """
---------------------------------------------------------------------------
Creates an VAR object by using the Vertica Highly Distributed and 
Scalable Linear Regression on the data.

Parameters
----------
name: str
    Name of the the model. The model will be stored in the DB.
cursor: DBcursor, optional
    Vertica DB cursor.
p: int, optional
    Order of the AR (Auto-Regressive) part.
penalty: str, optional
    Determines the method of regularization.
        None : No Regularization
        L1   : L1 Regularization
        L2   : L2 Regularization
        ENet : Combination between L1 and L2
tol: float, optional
    Determines whether the algorithm has reached the specified accuracy result.
C: float, optional
    The regularization parameter value. The value must be zero or non-negative.
max_iter: int, optional
    Determines the maximum number of iterations the algorithm performs before 
    achieving the specified accuracy result.
solver: str, optional
    The optimizer method to use to train the model. 
        Newton : Newton Method
        BFGS   : Broyden Fletcher Goldfarb Shanno
        CGD    : Coordinate Gradient Descent
l1_ratio: float, optional
    ENet mixture parameter that defines how much L1 versus L2 regularization 
    to provide.
    """

    def __init__(
        self,
        name: str,
        cursor=None,
        p: int = 1,
        penalty: str = "None",
        tol: float = 1e-4,
        C: float = 1.0,
        max_iter: int = 1000,
        solver: str = "Newton",
        l1_ratio: float = 0.5,
    ):
        check_types([("name", name, [str],)])
        self.type, self.name = "VAR", name
        assert p > 0, ParameterError(
            "Parameter 'p' must be greater than 0 to build a VAR model."
        )
        self.set_params(
            {
                "p": p,
                "penalty": penalty,
                "tol": tol,
                "C": C,
                "max_iter": max_iter,
                "solver": solver,
                "l1_ratio": l1_ratio,
            }
        )
        if not (cursor):
            cursor = read_auto_connect().cursor()
        else:
            check_cursor(cursor)
        self.cursor = cursor
        version(cursor=cursor, condition=[8, 0, 0])

    # ---#
    def deploySQL(self):
        """
    ---------------------------------------------------------------------------
    Returns the SQL code needed to deploy the model.

    Returns
    -------
    str
        the SQL code needed to deploy the model.
        """
        sql = []
        for idx, coefs in enumerate(self.coef_):
            coefs_tmp = coefs.values["coefficient"]
            predictors_tmp = coefs.values["predictor"]
            sql += [
                str(coefs_tmp[0])
                + " + "
                + " + ".join(
                    [
                        str(coefs_tmp[i]) + " * " + str(predictors_tmp[i])
                        for i in range(1, len(coefs_tmp))
                    ]
                )
            ]
        return sql

    # ---#
    def fit(self, input_relation: str, X: list, ts: str, test_relation: str = ""):
        """
    ---------------------------------------------------------------------------
    Trains the model.

    Parameters
    ----------
    input_relation: str
        Train relation.
    X: list
        List of the response columns.
    ts: str
        vcolumn used to order the data.
    test_relation: str, optional
        Relation to use to test the self.

    Returns
    -------
    object
        model
        """
        check_types(
            [
                ("input_relation", input_relation, [str],),
                ("X", X, [list],),
                ("ts", ts, [str],),
                ("test_relation", test_relation, [str],),
            ]
        )
        # Initialization
        check_model(name=self.name, cursor=self.cursor)
        self.input_relation = input_relation
        self.test_relation = test_relation if (test_relation) else input_relation
        self.ts, self.deploy_predict_ = str_column(ts), []
        self.X, schema = [str_column(elem) for elem in X], schema_relation(self.name)[0]
        model = ElasticNet(
            name=self.name,
            solver=self.parameters["solver"],
            max_iter=self.parameters["max_iter"],
            tol=self.parameters["tol"],
            penalty=self.parameters["penalty"],
            l1_ratio=self.parameters["l1_ratio"],
            C=self.parameters["C"],
        )

        # AR(p)
        columns, AR = [], []
        for idx, elem in enumerate(self.X):
            for i in range(1, self.parameters["p"] + 1):
                columns += [
                    "LAG([X{}], {}) OVER (ORDER BY [VerticaPy_ts]) AS AR{}_{}".format(
                        idx, i, idx, i
                    )
                ]
                AR += ["AR{}_{}".format(idx, i)]
        self.transform_relation = "(SELECT *, {} FROM {}) VERTICAPY_SUBTABLE".format(
            ", ".join(columns), "{}"
        )
        relation = self.transform_relation.replace("[VerticaPy_ts]", self.ts).format(
            input_relation
        )
        for idx, elem in enumerate(self.X):
            relation = relation.replace("[X{}]".format(idx), elem)
        try:
            drop_view(
                "{}.VERTICAPY_TEMP_MODEL_LINEAR_REGRESSION_VIEW_".format(schema),
                print_info=False,
            )
        except:
            pass
        query = "CREATE VIEW {}.VERTICAPY_TEMP_MODEL_LINEAR_REGRESSION_VIEW_ AS SELECT * FROM {}".format(
            schema, relation
        )
        self.cursor.execute(query)
        self.coef_ = []
        for elem in X:
            model.fit(
                input_relation="{}.VERTICAPY_TEMP_MODEL_LINEAR_REGRESSION_VIEW_".format(
                    schema
                ),
                X=AR,
                y=elem,
            )
            self.coef_ += [model.coef_]
            model.drop()
        drop_view(
            "{}.VERTICAPY_TEMP_MODEL_LINEAR_REGRESSION_VIEW_".format(schema),
            print_info=False,
        )
        return self

    # ---#
    def fpredict(self, L: list):
        """
    ---------------------------------------------------------------------------
    Computes the prediction.

    Parameters
    ----------
    L: list
        List containing the data. It must be a 2D list containing multiple rows.
        Each row must include as first element the ordered predictor and as 
        nth elements the nth - 1 exogenous variable (nth > 2). 

    Returns
    -------
    float
        the prediction.
        """
        try:
            result = []
            result_tmp = 0
            for i in range(len(self.X)):
                result_tmp = 0
                for j in range(len(self.coef_[i].values["coefficient"])):
                    elem = self.coef_[i].values["predictor"][j]
                    if elem.lower() == "intercept":
                        result_tmp += self.coef_[i].values["coefficient"][j]
                    else:
                        ni, nj = elem[2:].split("_")
                        ni, nj = int(ni), int(nj)
                        result_tmp += (
                            self.coef_[i].values["coefficient"][j] * L[-nj][ni]
                        )
                result += [result_tmp]
            return result
        except:
            raise
            return None

    # ---#
    def plot(
        self,
        vdf,
        X: list = [],
        ts: str = "",
        X_idx: int = 0,
        dynamic: bool = False,
        one_step: bool = True,
        observed: bool = True,
        confidence: bool = True,
        nlead: int = 10,
        nlast: int = 0,
        limit: int = 1000,
    ):
        """
    ---------------------------------------------------------------------------
    Draws the Plot of the prediction.

    Parameters
    ----------
    vdf: vDataFrame
        Object to use to run the prediction.
    X: list, optional
        List of the response columns.
    ts: str, optional
        vcolumn used to order the data.
    X_idx: int, optional
        Index of the main vector vcolumn to draw.
    dynamic: bool, optional
        If set to True, the dynamic forecast will be drawn.
    one_step: bool, optional
        If set to True, the one step ahead forecast will be drawn.
    observed: bool, optional
        If set to True, the observation will be drawn.
    confidence: bool, optional
        If set to True, the confidence ranges will be drawn.
    nlead: int, optional
        Number of leads to predict after the last ts date.
    limit: int, optional
        Maximum number of past elements to use.

    Returns
    -------
    Figure
        Matplotlib Figure
        """
        check_types(
            [
                ("limit", limit, [int, float],),
                ("nlead", nlead, [int, float],),
                ("X_idx", X_idx, [int, float],),
                ("dynamic", dynamic, [bool],),
                ("observed", observed, [bool],),
                ("one_step", one_step, [bool],),
                ("confidence", confidence, [bool],),
                ("vdf", vdf, [vDataFrame],),
            ],
        )
        delta_limit, limit = (
            limit,
            max(max(limit, self.parameters["p"] + 1 + nlast), 200),
        )
        delta_limit = max(limit - delta_limit - nlast, 0)
        assert dynamic or one_step or observed, ParameterError(
            "No option selected.\n You should set either dynamic, one_step or observed to True."
        )
        assert nlead + nlast > 0 or not (dynamic), ParameterError(
            "Dynamic Plots are only possible if either parameter 'nlead' is greater than 0 or parameter 'nlast' is greater than 0, and parameter 'dynamic' is set to True."
        )
        assert len(self.X) > X_idx >= 0, ParameterError(
            "The index of the vcolumn to draw 'X_idx' must be between 0 and {}".format(
                len(self.X)
            )
        )
        if not (ts):
            ts = self.ts
        if not (X):
            X = self.X
        result_all = self.predict(
            vdf=vdf,
            X=X,
            ts=ts,
            nlead=0,
            name=[
                "_verticapy_prediction_{}_".format(idx) for idx in range(len(self.X))
            ],
        )
        y, prediction = X[X_idx], "_verticapy_prediction_{}_".format(X_idx)
        error_eps = 1.96 * math.sqrt(self.score(method="mse").values["mse"][X_idx])
        result = (
            result_all.select([ts, y, prediction])
            .dropna(print_info=False)
            .sort([ts])
            .tail(limit)
            .values
        )
        columns = [elem for elem in result]
        if isinstance(result[columns[0]][0], str):
            result[columns[0]] = [parse(elem) for elem in result[columns[0]]]
        true_value = [result[columns[0]], result[columns[1]]]
        one_step_ahead = [result[columns[0]], result[columns[2]]]
        lower_osa, upper_osa = (
            [
                float(elem) - error_eps if elem != None else None
                for elem in one_step_ahead[1]
            ],
            [
                float(elem) + error_eps if elem != None else None
                for elem in one_step_ahead[1]
            ],
        )
        if dynamic:
            result = (
                result_all.select([ts] + X)
                .dropna(print_info=False)
                .sort([ts])
                .tail(limit)
                .values
            )
            columns = [elem for elem in result]
            if isinstance(result[columns[0]][0], str):
                result[columns[0]] = [parse(elem) for elem in result[columns[0]]]
            deltat = result[columns[0]][-1] - result[columns[0]][-2]
            lead_time_list, lead_list = [], []
            if nlast > 0:
                for i in range(len(result[columns[0]][:-nlast])):
                    lead_list += [[result[elem][i] for elem in columns[1:]]]
            else:
                for i in range(len(result[columns[0]])):
                    lead_list += [[result[elem][i] for elem in columns[1:]]]
            for i in range(nlast):
                lead_list += [self.fpredict(lead_list)]
                lead_time_list += [result[columns[0]][i - nlast]]
            if lead_time_list:
                start_time = lead_time_list[-1]
            else:
                start_time = result[columns[0]][-1]
            for i in range(nlead):
                lead_list += [self.fpredict(lead_list)]
                lead_time_list += [start_time + (i + 1) * deltat]
            dynamic_forecast = (
                [result[columns[0]][-nlast - 1]] + lead_time_list,
                [result[columns[1 + X_idx]][-nlast - 1]]
                + [elem[X_idx] for elem in lead_list[-nlast - nlead :]],
            )
            lower_d, upper_d = [], []
            for i in range(len(dynamic_forecast[1])):
                delta_error = error_eps * math.sqrt(i + 1)
                lower_d += [float(dynamic_forecast[1][i]) - delta_error]
                upper_d += [float(dynamic_forecast[1][i]) + delta_error]
        else:
            lower_d, upper_d, dynamic_forecast = [], [], ([], [])
        import matplotlib.pyplot as plt

        alpha = 0.3
        plt.figure(figsize=(12, 9)) if isnotebook() else plt.figure(figsize=(10, 6))
        plt.gca().grid()
        if dynamic:
            plt.fill_between(
                dynamic_forecast[0],
                1.02
                * float(min(true_value[1] + dynamic_forecast[1] + one_step_ahead[1])),
                1.02
                * float(max(true_value[1] + dynamic_forecast[1] + one_step_ahead[1])),
                alpha=0.04,
                color="#0073E7",
            )
            if confidence:
                plt.fill_between(
                    dynamic_forecast[0], lower_d, upper_d, alpha=0.08, color="#555555"
                )
                plt.plot(dynamic_forecast[0], lower_d, alpha=0.08, color="#000000")
                plt.plot(dynamic_forecast[0], upper_d, alpha=0.08, color="#000000")
            plt.plot(
                dynamic_forecast[0],
                dynamic_forecast[1],
                color="#FE5016",
                label="Dynamic Forecast",
                linestyle="dashed",
                linewidth=2,
            )
        if one_step:
            if confidence:
                plt.fill_between(
                    one_step_ahead[0][delta_limit:],
                    lower_osa[delta_limit:],
                    upper_osa[delta_limit:],
                    alpha=0.04,
                    color="#555555",
                )
                plt.plot(
                    one_step_ahead[0][delta_limit:],
                    lower_osa[delta_limit:],
                    alpha=0.04,
                    color="#000000",
                )
                plt.plot(
                    one_step_ahead[0][delta_limit:],
                    upper_osa[delta_limit:],
                    alpha=0.04,
                    color="#000000",
                )
            plt.plot(
                one_step_ahead[0][delta_limit:],
                one_step_ahead[1][delta_limit:],
                color="#19A26B",
                label="One-step ahead Forecast",
                linestyle=":",
                linewidth=2,
            )
        if observed:
            plt.plot(
                true_value[0][delta_limit:],
                true_value[1][delta_limit:],
                color="#0073E7",
                label="Observed",
                linewidth=2,
            )
        plt.rcParams["axes.facecolor"] = "#F2F2F2"
        plt.title("VAR({}) [{}]".format(self.parameters["p"], y))
        plt.xticks(rotation=90)
        plt.subplots_adjust(bottom=0.24)
        plt.xlabel(ts)
        plt.legend(loc="center left", bbox_to_anchor=[1, 0.5])
        plt.ylim(
            1.02 * float(min(true_value[1] + dynamic_forecast[1] + one_step_ahead[1])),
            1.02 * float(max(true_value[1] + dynamic_forecast[1] + one_step_ahead[1])),
        )
        return plt.gcf()

    # ---#
    def predict(self, vdf, X: list = [], ts: str = "", nlead: int = 0, name: list = []):
        """
    ---------------------------------------------------------------------------
    Predicts using the input relation.

    Parameters
    ----------
    vdf: vDataFrame
        Object to use to run the prediction.
    X: list, optional
        List of the response columns.
    ts: str, optional
        vcolumn used to order the data.
    nlead: int, optional
        Number of leads to predict after the last ts date.
    name: list, optional
        Name of the added vcolumns. If empty, names will be generated.

    Returns
    -------
    vDataFrame
        object including the prediction.
        """
        check_types(
            [
                ("name", name, [list],),
                ("ts", ts, [str],),
                ("nlead", nlead, [int, float],),
                ("X", X, [list],),
            ],
            ("vdf", vdf, [vDataFrame],),
        )
        if not (ts):
            ts = self.ts
        if not (X):
            X = self.X
        columns_check(X + [ts], vdf)
        X = vdf_columns_names(X, vdf)
        ts = vdf_columns_names([ts], vdf)[0]
        all_pred, names = [], []
        transform_relation = self.transform_relation.replace("[VerticaPy_ts]", self.ts)
        for idx, elem in enumerate(X):
            name_tmp = (
                "{}_".format(self.type) + "".join(ch for ch in elem if ch.isalnum())
                if len(name) != len(X)
                else name[idx]
            )
            all_pred += ["{} AS {}".format(self.deploySQL()[idx], name_tmp)]
            transform_relation = transform_relation.replace("[X{}]".format(idx), elem)
        columns = vdf.get_columns() + all_pred
        relation = vdf.__genSQL__()
        for i in range(nlead):
            query = "SELECT ({} - LAG({}, 1) OVER (ORDER BY {}))::VARCHAR FROM {} ORDER BY {} DESC LIMIT 1".format(
                ts, ts, ts, relation, ts
            )
            deltat = vdf._VERTICAPY_VARIABLES_["cursor"].execute(query).fetchone()[0]
            query = "SELECT (MAX({}) + '{}'::interval)::VARCHAR FROM {}".format(
                ts, deltat, relation
            )
            next_t = vdf._VERTICAPY_VARIABLES_["cursor"].execute(query).fetchone()[0]
            if i == 0:
                first_t = next_t
            new_line = "SELECT '{}'::TIMESTAMP AS {}, {}".format(
                next_t,
                ts,
                ", ".join(
                    [
                        "NULL AS {}".format(column)
                        for column in vdf.get_columns(exclude_columns=[ts])
                    ]
                ),
            )
            relation_tmp = "(SELECT {} FROM {} UNION ALL ({})) VERTICAPY_SUBTABLE".format(
                ", ".join([ts] + vdf.get_columns(exclude_columns=[ts])),
                relation,
                new_line,
            )
            query = "SELECT {} FROM {} ORDER BY {} DESC LIMIT 1".format(
                ", ".join(self.deploySQL()), transform_relation.format(relation_tmp), ts
            )
            prediction = vdf._VERTICAPY_VARIABLES_["cursor"].execute(query).fetchone()
            for idx, elem in enumerate(X):
                prediction[idx] = "{} AS {}".format(prediction[idx], elem)
            columns_tmp = vdf.get_columns(exclude_columns=[ts] + X)
            new_line = "SELECT '{}'::TIMESTAMP AS {}, {} {}".format(
                next_t,
                ts,
                ", ".join(prediction),
                (", " if (columns_tmp) else "")
                + ", ".join(["NULL AS {}".format(column) for column in columns_tmp]),
            )
            relation = "(SELECT {} FROM {} UNION ALL ({})) VERTICAPY_SUBTABLE".format(
                ", ".join([ts] + X + vdf.get_columns(exclude_columns=[ts] + X)),
                relation,
                new_line,
            )
        final_relation = "(SELECT {} FROM {}) VERTICAPY_SUBTABLE".format(
            ", ".join(columns), transform_relation.format(relation)
        )
        result = vdf_from_relation(final_relation, "VAR", self.cursor,)
        if nlead > 0:
            for elem in X:
                result[elem].apply(
                    "CASE WHEN {} >= '{}' THEN NULL ELSE {} END".format(
                        ts, first_t, "{}"
                    )
                )
        return result
