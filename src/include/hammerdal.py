from .. import models


class Record:
    sql=''


def insertToHammerLog(r: models.ReqModel):
    return


def insertToHammerError(ex: Exception, creator, buildLink, selectedAwsAccount, buildTypeId, msg, isUserError):
    return


def insertToModifyJobLog(mm, buildId, buildLink):  #mm is models.ModifyInstanceModel
    return


def selectHammerlogState():
    return


def updateec2instanceState(items):
    return


def insertEC2instance(tNode: models.TableauNode, primaryNodeInstanceId, nodeCount):
    return


def insertEC2count(targetaws, accountid, accountname, budgetgroup, reportdate, ec2_count_total, ec2_count_hammerhead):
    return


def select_ec2instance():
    return

