module FprimeYamcsReference {

  # ----------------------------------------------------------------------
  # Symbolic constants for port numbers
  # ----------------------------------------------------------------------

  enum Ports_RateGroups {
    rateGroup1
    rateGroup2
    rateGroup3
  }

  topology YamcsDeployment {

  # ----------------------------------------------------------------------
  # Subtopology instances
  # ----------------------------------------------------------------------
    instance CdhCore.Subtopology
    instance ComCcsds.Subtopology
    instance DataProducts.Subtopology
    instance FileHandling.Subtopology
    
  # ----------------------------------------------------------------------
  # Instances used in the topology
  # ----------------------------------------------------------------------
    instance chronoTime
    instance rateGroup1
    instance rateGroup2
    instance rateGroup3
    instance rateGroupDriver
    instance systemResources
    instance timer
    instance comDriver
    instance cmdSeq

  # ----------------------------------------------------------------------
  # Pattern graph specifiers
  # ----------------------------------------------------------------------

    command connections instance CdhCore.cmdDisp
    event connections instance CdhCore.events
    telemetry connections instance CdhCore.tlmSend
    text event connections instance CdhCore.textLogger
    health connections instance CdhCore.$health
    param connections instance FileHandling.prmDb
    time connections instance chronoTime

  # ----------------------------------------------------------------------
  # Telemetry packets (only used when TlmPacketizer is used)
  # ----------------------------------------------------------------------

  include "YamcsDeploymentPackets.fppi"

  # ----------------------------------------------------------------------
  # Direct graph specifiers
  # ----------------------------------------------------------------------

    connections ComCcsds_CdhCore {
      # Core events and telemetry to communication queue
      CdhCore.Subtopology.eventsPktSend -> ComCcsds.Subtopology.comPacketQueueIn[ComCcsds.Ports_ComPacketQueue.EVENTS]
      CdhCore.Subtopology.tlmSendPktSend -> ComCcsds.Subtopology.comPacketQueueIn[ComCcsds.Ports_ComPacketQueue.TELEMETRY]

      # Router to Command Dispatcher
      ComCcsds.Subtopology.commandOut -> CdhCore.Subtopology.seqCmdBuff
      CdhCore.Subtopology.seqCmdStatus -> ComCcsds.Subtopology.cmdResponseIn

    }

    connections ComCcsds_FileHandling {
      # File Downlink to Communication Queue
      FileHandling.Subtopology.fileDownlinkBufferSendOut -> ComCcsds.Subtopology.bufferQueueIn[ComCcsds.Ports_ComBufferQueue.FILE]
      ComCcsds.Subtopology.bufferReturnOut[ComCcsds.Ports_ComBufferQueue.FILE] -> FileHandling.Subtopology.fileDownlinkBufferReturn

      # Router to File Uplink
      ComCcsds.Subtopology.fileUplinkOut -> FileHandling.Subtopology.fileUplinkBufferSendIn
      FileHandling.Subtopology.fileUplinkBufferSendOut -> ComCcsds.Subtopology.fileUplinkReturnIn
    }

    connections Communications {
      # ComDriver buffer allocations
      comDriver.allocate      -> ComCcsds.Subtopology.commsBufferGetCallee
      comDriver.deallocate    -> ComCcsds.Subtopology.commsBufferSendIn

      # ComDriver <-> ComStub (Uplink)
      comDriver.$recv                     -> ComCcsds.Subtopology.drvReceiveIn
      ComCcsds.Subtopology.drvReceiveReturnOut -> comDriver.recvReturnIn

      # ComStub <-> ComDriver (Downlink)
      ComCcsds.Subtopology.drvSendOut      -> comDriver.$send
      comDriver.ready         -> ComCcsds.Subtopology.drvConnected
    }

    connections FileHandling_DataProducts {
      # Data Products to File Downlink
      DataProducts.Subtopology.dpCatFileOut -> FileHandling.Subtopology.fileDownlinkSendFile
      FileHandling.Subtopology.fileDownlinkFileComplete -> DataProducts.Subtopology.dpCatFileDone
    }

    connections RateGroups {
      # timer to drive rate group
      timer.CycleOut -> rateGroupDriver.CycleIn

      # Rate group 1
      rateGroupDriver.CycleOut[Ports_RateGroups.rateGroup1] -> rateGroup1.CycleIn
      rateGroup1.RateGroupMemberOut[0] -> CdhCore.Subtopology.tlmSendRun
      rateGroup1.RateGroupMemberOut[1] -> FileHandling.Subtopology.fileDownlinkRun
      rateGroup1.RateGroupMemberOut[2] -> systemResources.run
      rateGroup1.RateGroupMemberOut[3] -> ComCcsds.Subtopology.comQueueRun
      rateGroup1.RateGroupMemberOut[4] -> ComCcsds.Subtopology.aggregatorTimeout
      rateGroup1.RateGroupMemberOut[5] -> FileHandling.Subtopology.fileManagerSchedIn
      rateGroup1.RateGroupMemberOut[6] -> CdhCore.Subtopology.cmdDispRun

      # Rate group 2
      rateGroupDriver.CycleOut[Ports_RateGroups.rateGroup2] -> rateGroup2.CycleIn
      rateGroup2.RateGroupMemberOut[0] -> cmdSeq.schedIn

      # Rate group 3
      rateGroupDriver.CycleOut[Ports_RateGroups.rateGroup3] -> rateGroup3.CycleIn
      rateGroup3.RateGroupMemberOut[0] -> CdhCore.Subtopology.healthRun
      rateGroup3.RateGroupMemberOut[1] -> ComCcsds.Subtopology.bufferManagerSchedIn
      rateGroup3.RateGroupMemberOut[2] -> DataProducts.Subtopology.dpBufferManagerSchedIn
      rateGroup3.RateGroupMemberOut[3] -> DataProducts.Subtopology.dpWriterSchedIn
      rateGroup3.RateGroupMemberOut[4] -> DataProducts.Subtopology.dpMgrSchedIn
    }

    connections CdhCore_cmdSeq {
      # Command Sequencer
      cmdSeq.comCmdOut -> CdhCore.Subtopology.seqCmdBuff
      CdhCore.Subtopology.seqCmdStatus -> cmdSeq.cmdResponseIn
    }

    connections YamcsDeployment {

    }

  }

}
