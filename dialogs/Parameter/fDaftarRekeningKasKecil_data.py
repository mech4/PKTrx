import com.ihsan.foundation.pobjecthelper as phelper
import sys

def GetDataBank(config,parameters,returns):
  status = returns.CreateValues(
    ['IsErr',0],
    ['ErrMessage','']
  )

  dsData = returns.AddNewDatasetEx(
      'MasterData',
    ';'.join([
      'AccountNo: string',
      'CashCode: string',
      'AccountName: string',
      'UserName: string',
      'BranchCode: string',
      'BranchName: string',
      'CurrencyCode: string',
      'CurrencyName: string',
      'Balance: float',
      'Status: string',
    ])
  )

  try:
    helper = phelper.PObjectHelper(config)
    corporate = helper.CreateObject('Corporate')

    dStatus = {'A' : 'Active','N' : 'Not Active'}

    strOQL = "select from PettyCash \
      ( \
        AccountNo, \
        CashCode, \
        AccountName, \
        UserName, \
        Balance, \
        BranchCode, \
        CurrencyCode, \
        OpeningDate, \
        Status, \
        LCurrency.Short_name, \
        self \
      ) then order by BranchCode,AccountNo;"

    oql = config.OQLEngine.CreateOQL(strOQL)
    oql.active = 1
    oRes  = oql.rawresult
    oRes.First()
    dictCabang = {}
    while not oRes.Eof:
      recData = dsData.AddRecord()
      recData.AccountNo = oRes.AccountNo
      recData.CashCode = oRes.CashCode
      recData.AccountName = oRes.AccountName

      BranchCode = oRes.BranchCode
      if not dictCabang.has_key(BranchCode):
        CabangInfo = corporate.GetCabangInfo(BranchCode)
        dictCabang[BranchCode] = CabangInfo.Nama_Cabang
      recData.BranchCode = BranchCode
      recData.BranchName = dictCabang[BranchCode]
      recData.UserName = oRes.UserName
      recData.CurrencyCode = oRes.CurrencyCode
      recData.CurrencyName = oRes.Short_Name
      recData.Balance = oRes.Balance
      recData.Status = dStatus[oRes.Status]

      oRes.Next()
    # end while

  except:
    status.IsErr = 1
    status.ErrMessage = str(sys.exc_info()[1])
